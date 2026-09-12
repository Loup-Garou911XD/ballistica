# Released under the MIT License. See LICENSE for details.
#
"""Wire protocol for talking to a BombSquad host as a remote controller.

Pure encode/decode helpers -- no sockets, no engine calls -- so this can
be exercised directly by tests. The authoritative definition of every
layout here is the host side, which lives in the ``base`` feature-set at
``src/ballistica/base/input/support/remote_app_server.cc``.
"""

import struct
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Sequence

#: Port the host listens on (``kDefaultPort`` in shared/ballistica.h).
PORT = 43210

#: Must match ``kRemoteAppProtocolVersion``; the host hangs up otherwise.
PROTOCOL_VERSION = 121

#: Sent as the 5th byte of an id-request to ask for 24-bit ('v2') states.
#: The host answers with :data:`PROTOCOL_RESPONSE_V2` to confirm. This is
#: the only usable path -- a host that doesn't confirm will reject every
#: state packet we go on to send.
PROTOCOL_REQUEST_V2 = 50
PROTOCOL_RESPONSE_V2 = 100

#: The host reads at most this many bytes of name, and caps total
#: id-request length at 127.
MAX_NAME_BYTES = 100

# Packet types (first byte of the datagram).
PACKET_ID_REQUEST = 2
PACKET_ID_RESPONSE = 3
PACKET_DISCONNECT = 4
PACKET_STATE_ACK = 6
PACKET_DISCONNECT_ACK = 7
PACKET_GAME_QUERY = 8
PACKET_GAME_RESPONSE = 9
PACKET_STATE2 = 10

# Button bits; these live in byte 0 of each 3-byte state entry.
BUTTON_MENU = 0x01
BUTTON_JUMP = 0x02
BUTTON_PUNCH = 0x04
BUTTON_THROW = 0x08
BUTTON_BOMB = 0x10
BUTTON_RUN = 0x20
BUTTON_FLY = 0x40  # Defined by the host but never decoded by it.
BUTTON_HOLD_POSITION = 0x80


class RemoteError(Enum):
    """Reason a host gave for hanging up on us."""

    VERSION_MISMATCH = 0
    GAME_SHUTTING_DOWN = 1
    NOT_ACCEPTING_CONNECTIONS = 2
    NOT_CONNECTED = 3


def encode_name(name: str, tag: str | None = None) -> bytes:
    """Encode a controller name, optionally with a uniquifying tag.

    The host uses the whole string as the identity key for slot reuse but
    shows only the part before ``#``, so passing a stable per-install
    ``tag`` is what lets a reconnect land back in the same slot instead
    of consuming a second one.
    """
    full = name if tag is None else f'{name}#{tag}'
    encoded = full.encode('utf-8')

    if len(encoded) <= MAX_NAME_BYTES:
        return encoded

    # Truncate on a character boundary so we never ship half a codepoint.
    return encoded[:MAX_NAME_BYTES].decode('utf-8', 'ignore').encode('utf-8')


def axis_byte(value: float) -> int:
    """Quantize a -1..1 axis to the byte the host expects.

    The host decodes with ``-1.0 + 2.0 * (raw / 255.0)``, so exact centre
    is not representable; 128 lands on +0.004. That tiny offset is why v2
    clients get joystick calibration turned on host-side.
    """
    return max(0, min(255, round((value + 1.0) * 127.5)))


def pack_game_query() -> bytes:
    """Build the discovery broadcast."""
    return bytes([PACKET_GAME_QUERY])


def parse_game_response(data: bytes) -> str | None:
    """Pull the host's display name out of a discovery reply."""
    if len(data) < 1 or data[0] != PACKET_GAME_RESPONSE:
        return None

    # Not NUL-terminated on the wire, but the host builds it in a fixed
    # 256-byte buffer, so a trailing NUL can still show up.
    return data[1:].split(b'\0', 1)[0].decode('utf-8', 'replace')


def pack_id_request(request_id: int, name: bytes) -> bytes:
    """Build the handshake packet.

    ``request_id`` is memcpy'd as a native-endian int16 on the host side.
    Every platform we target is little-endian, so '<h' is correct, but
    that is the reason it is not network byte order.
    """
    if len(name) > MAX_NAME_BYTES:
        raise ValueError('name too long; use encode_name()')

    return (
        struct.pack(
            '<BBhB',
            PACKET_ID_REQUEST,
            PROTOCOL_VERSION,
            request_id,
            PROTOCOL_REQUEST_V2,
        )
        + name
    )


def parse_id_response(data: bytes) -> tuple[int, int] | None:
    """Return ``(client_id, protocol_response)`` from an accept packet."""
    if len(data) < 3 or data[0] != PACKET_ID_RESPONSE:
        return None
    return data[1], data[2]


def parse_disconnect(data: bytes) -> RemoteError | None:
    """Return the reason from a host-initiated disconnect."""
    if len(data) < 2 or data[0] != PACKET_DISCONNECT:
        return None
    try:
        return RemoteError(data[1])
    except ValueError:
        return None


def pack_state(buttons: int, axis_h: float, axis_v: float) -> bytes:
    """Build one 3-byte state entry."""
    return bytes([buttons & 0xFF, axis_byte(axis_h), axis_byte(axis_v)])


def pack_state_packet(
    client_id: int, start_state_id: int, states: Sequence[bytes]
) -> bytes:
    """Bundle a run of consecutive states into one packet.

    The host validates length as exactly ``4 + count * 3`` and drops the
    packet otherwise, so every entry must be 3 bytes.
    """
    if not states:
        raise ValueError('need at least one state')
    if len(states) > 255:
        raise ValueError('state count must fit in a byte')
    if any(len(s) != 3 for s in states):
        raise ValueError('states must be 3 bytes each')

    return struct.pack(
        '<BBBB',
        PACKET_STATE2,
        client_id,
        len(states),
        start_state_id & 0xFF,
    ) + b''.join(states)


def parse_state_ack(data: bytes) -> int | None:
    """Return the next state-id the host wants.

    This doubles as the host's heartbeat -- there is no separate
    keepalive packet in either direction.
    """
    if len(data) < 2 or data[0] != PACKET_STATE_ACK:
        return None
    return data[1]


def pack_disconnect(client_id: int) -> bytes:
    """Build a clean goodbye.

    Worth sending: the host frees slots only on an explicit disconnect,
    never on a timeout.
    """
    return bytes([PACKET_DISCONNECT, client_id])


def is_disconnect_ack(data: bytes) -> bool:
    """Whether this is the host acknowledging our goodbye."""
    return len(data) >= 1 and data[0] == PACKET_DISCONNECT_ACK
