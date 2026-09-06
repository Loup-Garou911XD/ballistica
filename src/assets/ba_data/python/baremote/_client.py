# Released under the MIT License. See LICENSE for details.
#
"""Network client for talking to a BombSquad host as a controller."""

import time
import random
import select
import socket
import logging
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import babase

from baremote import _protocol

if TYPE_CHECKING:
    from typing import Callable

    from baremote._state import RemoteState

logger = logging.getLogger('ba.remote')

#: How often we resend the discovery broadcast while scanning.
_SCAN_INTERVAL = 1.0

#: A host we haven't heard from in this long drops off the list.
_HOST_EXPIRE = 5.0

#: Handshake resend interval and overall give-up time.
_HANDSHAKE_INTERVAL = 0.5
_HANDSHAKE_TIMEOUT = 5.0

#: State packet rate. The host applies states in order, so this is also
#: our input resolution.
_STATE_INTERVAL = 1.0 / 30.0

#: How many unacked states we keep around to retransmit. Every one of
#: them rides along in each packet, which is what keeps the host from
#: stalling: it applies only the state whose id matches the next one it
#: wants, and fast-forwards over a gap only when that gap exceeds 10. If
#: we sent a subset we could sit just inside that threshold with the
#: states the host is waiting for no longer in flight. At 3 bytes each
#: the whole window is under 100 bytes, so there is nothing to save by
#: trimming it.
_MAX_UNACKED = 30


class ConnectionState(Enum):
    """Where the client currently is."""

    IDLE = 'idle'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'


@dataclass
class HostInfo:
    """A host that answered our discovery broadcast."""

    address: str
    name: str
    last_seen: float = field(default=0.0)


def _local_addresses() -> set[str]:
    """Best-effort set of this machine's own IPv4 addresses.

    We need these because our own process is also listening on the game
    port and answers discovery unconditionally, so without filtering the
    remote would happily list itself as a host.
    """
    addrs: set[str] = set()

    # The address we'd use to reach the outside world. UDP connect sends
    # nothing, it just picks a route.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('8.8.8.8', 1))
        addrs.add(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()

    try:
        addrs.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass

    addrs.add('127.0.0.1')
    return addrs


def _broadcast_addresses() -> list[str]:
    """Addresses worth aiming a discovery broadcast at.

    There is no engine helper exposed to Python for this, so we take the
    global broadcast plus a /24 guess per local address. Anything more
    exotic is what the manual-address field is for.
    """
    out = ['255.255.255.255']
    for addr in _local_addresses():
        if addr.startswith('127.'):
            continue
        parts = addr.split('.')
        if len(parts) == 4:
            guess = '.'.join(parts[:3] + ['255'])
            if guess not in out:
                out.append(guess)
    return out


class RemoteClient:
    """Drives the remote-app protocol on a background thread.

    All callbacks are delivered on the logic thread, so handlers can
    touch the UI directly.
    """

    def __init__(self, state: RemoteState) -> None:
        self._state = state

        #: Assigned by the caller; all fire on the logic thread.
        self.on_hosts_changed: Callable[[list[HostInfo]], None] | None = None
        self.on_connected: Callable[[], None] | None = None
        self.on_disconnected: Callable[[str | None], None] | None = None

        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._sock: socket.socket | None = None

        self._local_addrs: set[str] = set()
        self._scanning = False
        self._last_scan_send = 0.0
        self._hosts: dict[str, HostInfo] = {}

        self._connstate = ConnectionState.IDLE
        self._host_addr: tuple[str, int] | None = None
        self._name = b''
        self._request_id = 0
        self._client_id = 0
        self._handshake_started = 0.0
        self._last_handshake_send = 0.0

        self._next_state_id = 0
        self._unacked: list[tuple[int, bytes]] = []
        self._last_state_send = 0.0

        #: Highest ack seen this connection. UDP reorders and duplicates
        #: freely, and an old ack must not be allowed to drag our
        #: counter backwards -- see _handle_state_ack.
        self._last_ack: int | None = None

    # -------------------------------------------------------------- lifecycle

    def start(self) -> None:
        """Bring the socket and worker thread up."""
        assert self._thread is None

        self._local_addrs = _local_addresses()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Port 0: the host replies to whatever source port we send from,
        # so we must not fight the engine for the game port.
        sock.bind(('', 0))
        sock.setblocking(False)
        self._sock = sock

        self._thread = threading.Thread(
            target=self._run, name='baremote-client', daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Say goodbye if connected, then shut the thread down."""
        if self._thread is None:
            return

        self.disconnect()
        self._stop.set()
        self._thread.join(timeout=2.0)
        self._thread = None

        if self._sock is not None:
            self._sock.close()
            self._sock = None

    # ------------------------------------------------------------- public api

    def set_scanning(self, scanning: bool) -> None:
        """Start or stop broadcasting for hosts."""
        with self._lock:
            self._scanning = scanning
            if not scanning:
                self._hosts.clear()
            else:
                # Send one immediately rather than waiting out a tick.
                self._last_scan_send = 0.0

    def connect(self, address: str, name: str, tag: str) -> None:
        """Begin a handshake with the host at ``address``."""
        with self._lock:
            self._host_addr = (address, _protocol.PORT)
            self._name = _protocol.encode_name(name, tag)
            self._request_id = random.randint(0, 0x7FFF)
            self._connstate = ConnectionState.CONNECTING
            self._handshake_started = time.monotonic()
            self._last_handshake_send = 0.0
            self._next_state_id = 0
            self._unacked.clear()
            self._last_ack = None

    def disconnect(self) -> None:
        """Tell the host we're leaving and go idle."""
        with self._lock:
            connected = self._connstate is ConnectionState.CONNECTED
            addr = self._host_addr
            client_id = self._client_id
            self._connstate = ConnectionState.IDLE
            self._unacked.clear()

        if connected and addr is not None and self._sock is not None:
            # The host frees slots only on an explicit goodbye, so this
            # is worth a couple of tries in case one is dropped.
            for _ in range(3):
                self._send(_protocol.pack_disconnect(client_id), addr)

        self._set_input_attached(False)

    @property
    def connection_state(self) -> ConnectionState:
        """Current connection state."""
        with self._lock:
            return self._connstate

    # ---------------------------------------------------------------- interna

    def _send(self, data: bytes, addr: tuple[str, int]) -> None:
        sock = self._sock
        if sock is None:
            return
        try:
            sock.sendto(data, addr)
        except OSError as exc:
            # Unreachable networks and the like are routine here; a
            # broadcast to an interface that just went away shouldn't
            # take the thread down.
            logger.debug('remote send to %s failed: %s', addr, exc)

    def _push(self, call: Callable[[], None]) -> None:
        """Run something on the logic thread.

        Safe from either side; see _set_input_attached for why that
        matters.
        """
        if babase.in_logic_thread():
            call()
        else:
            babase.pushcall(call, from_other_thread=True)

    def _set_input_attached(self, attached: bool) -> None:
        # Native gating has to happen on the logic thread. disconnect()
        # is reachable from both threads (app-mode deactivate and app
        # shutdown both call it from the logic thread), and pushcall
        # complains if handed from_other_thread while already there.
        def _do() -> None:
            import _baremote

            _baremote.set_input_attached(attached)

        if babase.in_logic_thread():
            _do()
        else:
            self._push(_do)

    def _run(self) -> None:
        sock = self._sock
        assert sock is not None

        while not self._stop.is_set():
            try:
                readable, _, _ = select.select([sock], [], [], 0.01)
                if readable:
                    self._drain(sock)
                self._tick()
            except Exception:
                logger.exception('error in remote client loop')
                time.sleep(0.1)

    def _drain(self, sock: socket.socket) -> None:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
            except BlockingIOError:
                return
            except OSError:
                return
            self._handle_packet(data, addr)

    def _handle_packet(self, data: bytes, addr: tuple[str, int]) -> None:
        if not data:
            return

        ptype = data[0]

        if ptype == _protocol.PACKET_GAME_RESPONSE:
            self._handle_game_response(data, addr)
        elif ptype == _protocol.PACKET_ID_RESPONSE:
            self._handle_id_response(data, addr)
        elif ptype == _protocol.PACKET_STATE_ACK:
            self._handle_state_ack(data)
        elif ptype == _protocol.PACKET_DISCONNECT:
            self._handle_host_disconnect(data)
        elif ptype == _protocol.PACKET_DISCONNECT_ACK:
            pass

    def _handle_game_response(self, data: bytes, addr: tuple[str, int]) -> None:
        # Skip ourselves; our own engine answers these unconditionally.
        if addr[0] in self._local_addrs:
            return

        name = _protocol.parse_game_response(data)
        if name is None:
            return

        with self._lock:
            if not self._scanning:
                return
            existing = self._hosts.get(addr[0])
            changed = existing is None or existing.name != name
            self._hosts[addr[0]] = HostInfo(
                address=addr[0], name=name, last_seen=time.monotonic()
            )

        if changed:
            self._report_hosts()

    def _handle_id_response(self, data: bytes, addr: tuple[str, int]) -> None:
        parsed = _protocol.parse_id_response(data)
        if parsed is None:
            return
        client_id, proto = parsed

        with self._lock:
            if self._connstate is not ConnectionState.CONNECTING:
                return
            if self._host_addr is None or addr[0] != self._host_addr[0]:
                return

            if proto != _protocol.PROTOCOL_RESPONSE_V2:
                # The host accepted us but not the 24-bit state format,
                # which means every state packet we send would be
                # rejected. Treat that as a failure to connect.
                self._connstate = ConnectionState.IDLE
                self._report_disconnected('This host is too old.')
                return

            self._client_id = client_id
            self._connstate = ConnectionState.CONNECTED
            self._last_state_send = 0.0

        self._set_input_attached(True)
        if self.on_connected is not None:
            call = self.on_connected
            self._push(call)

    def _handle_state_ack(self, data: bytes) -> None:
        nextid = _protocol.parse_state_ack(data)
        if nextid is None:
            return

        with self._lock:
            # Ignore anything that isn't newer than the best ack we've
            # already seen. UDP delivers duplicates and reorders, and a
            # stale ack reaching the resync below would rewind our
            # counter and stall input until we caught back up.
            if self._last_ack is not None:
                if ((nextid - self._last_ack) & 0xFF) >= 128:
                    return
            self._last_ack = nextid

            # Drop everything the host has already consumed. The
            # comparison is mod-256 with a half-range window so wrapped
            # ids sort correctly.
            while self._unacked:
                diff = (nextid - self._unacked[0][0]) & 0xFF
                if 0 < diff < 128:
                    self._unacked.pop(0)
                else:
                    break

            # If the host is waiting on an id we aren't about to send,
            # our numbering has drifted from theirs. That happens on
            # reconnect: the host keeps its old counter when it reuses a
            # slot by name, but zeroes it when it allocates a fresh one,
            # and we can't tell which happened. Its fast-forward only
            # covers gaps wider than 10, so a small drift would
            # otherwise leave input dead until our counter wrapped all
            # the way around. Re-seed from what it just told us instead.
            if self._unacked and self._unacked[0][0] != nextid:
                self._unacked.clear()
                self._next_state_id = nextid

    def _handle_host_disconnect(self, data: bytes) -> None:
        err = _protocol.parse_disconnect(data)

        with self._lock:
            if self._connstate is ConnectionState.IDLE:
                return
            self._connstate = ConnectionState.IDLE
            self._unacked.clear()

        self._set_input_attached(False)
        self._report_disconnected(_describe_error(err))

    def _tick(self) -> None:
        now = time.monotonic()

        with self._lock:
            scanning = self._scanning
            connstate = self._connstate
            host_addr = self._host_addr

        if scanning and now - self._last_scan_send >= _SCAN_INTERVAL:
            self._last_scan_send = now
            query = _protocol.pack_game_query()
            for baddr in _broadcast_addresses():
                self._send(query, (baddr, _protocol.PORT))
            self._expire_hosts(now)

        if connstate is ConnectionState.CONNECTING and host_addr is not None:
            self._tick_handshake(now, host_addr)
        elif connstate is ConnectionState.CONNECTED and host_addr is not None:
            self._tick_state(now, host_addr)

    def _tick_handshake(self, now: float, addr: tuple[str, int]) -> None:
        if now - self._handshake_started > _HANDSHAKE_TIMEOUT:
            with self._lock:
                self._connstate = ConnectionState.IDLE
            self._report_disconnected('No response from host.')
            return

        if now - self._last_handshake_send < _HANDSHAKE_INTERVAL:
            return

        self._last_handshake_send = now
        self._send(
            _protocol.pack_id_request(self._request_id, self._name), addr
        )

    def _tick_state(self, now: float, addr: tuple[str, int]) -> None:
        if now - self._last_state_send < _STATE_INTERVAL:
            return
        self._last_state_send = now

        snapshot = self._state.snapshot()

        with self._lock:
            self._unacked.append((self._next_state_id, snapshot))
            self._next_state_id = (self._next_state_id + 1) & 0xFF

            # If the host has gone quiet, don't grow without bound.
            # Dropping the oldest opens a gap wide enough for the host's
            # fast-forward to skip it once it starts listening again.
            while len(self._unacked) > _MAX_UNACKED:
                self._unacked.pop(0)

            start_id = self._unacked[0][0]
            states = [s for _, s in self._unacked]
            client_id = self._client_id

        self._send(
            _protocol.pack_state_packet(client_id, start_id, states), addr
        )

    def _expire_hosts(self, now: float) -> None:
        with self._lock:
            stale = [
                addr
                for addr, info in self._hosts.items()
                if now - info.last_seen > _HOST_EXPIRE
            ]
            for addr in stale:
                del self._hosts[addr]

        if stale:
            self._report_hosts()

    def _report_hosts(self) -> None:
        if self.on_hosts_changed is None:
            return
        with self._lock:
            hosts = sorted(self._hosts.values(), key=lambda h: h.name)
        call = self.on_hosts_changed
        self._push(lambda: call(hosts))

    def _report_disconnected(self, reason: str | None) -> None:
        if self.on_disconnected is None:
            return
        call = self.on_disconnected
        self._push(lambda: call(reason))


def _describe_error(err: _protocol.RemoteError | None) -> str | None:
    if err is _protocol.RemoteError.VERSION_MISMATCH:
        return 'Version mismatch with host.'
    if err is _protocol.RemoteError.GAME_SHUTTING_DOWN:
        return 'The host is shutting down.'
    if err is _protocol.RemoteError.NOT_ACCEPTING_CONNECTIONS:
        return 'The host is not accepting connections.'
    if err is _protocol.RemoteError.NOT_CONNECTED:
        return 'The host dropped our connection.'
    return None
