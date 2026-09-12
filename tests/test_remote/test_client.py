# Released under the MIT License. See LICENSE for details.
#
"""Tests for remote client bookkeeping.

Exercises the ack/retransmit window directly. RemoteClient's constructor
touches no sockets and starts no thread, so this stays a pure unit test.
"""

# Reaching into the retransmit window is the point here.
# pylint: disable=protected-access

from baremote._client import RemoteClient
from baremote._state import RemoteState


def _client() -> RemoteClient:
    return RemoteClient(RemoteState())


def _ack(nextid: int) -> bytes:
    return bytes([6, nextid])


def test_ack_drops_consumed_states() -> None:
    """States the host has consumed leave the retransmit window."""
    client = _client()
    client._unacked = [(n, b'\x00\x80\x80') for n in range(5)]

    client._handle_state_ack(_ack(3))

    assert [n for n, _ in client._unacked] == [3, 4]


def test_ack_handles_wrapped_ids() -> None:
    """Ids are a single byte, so the window must survive a wrap."""
    client = _client()
    # Ids 253, 254, 255, 0, 1.
    client._unacked = [
        (n & 0xFF, b'\x00\x80\x80') for n in (253, 254, 255, 256, 257)
    ]

    client._handle_state_ack(_ack(1))

    # Everything before the wrap is consumed; only the id the host is
    # actually waiting on survives.
    assert [n for n, _ in client._unacked] == [1]


def test_ack_resyncs_on_drift() -> None:
    """A host asking for an id we aren't sending re-seeds our counter.

    This is the reconnect case: the host keeps its old counter when it
    reuses a slot by name, so it can be waiting on an id our fresh
    numbering would not reach for hundreds of ticks.
    """
    client = _client()
    client._next_state_id = 5
    client._unacked = [(n, b'\x00\x80\x80') for n in range(5)]

    # Host wants 200 -- far from anything in our window.
    client._handle_state_ack(_ack(200))

    assert not client._unacked
    assert client._next_state_id == 200


def test_ack_in_sync_is_left_alone() -> None:
    """The normal case must not trigger a resync."""
    client = _client()
    client._next_state_id = 5
    client._unacked = [(n, b'\x00\x80\x80') for n in range(5)]

    client._handle_state_ack(_ack(4))

    assert [n for n, _ in client._unacked] == [4]
    assert client._next_state_id == 5


def test_stale_ack_does_not_rewind() -> None:
    """A duplicated or reordered ack must not drag the counter back.

    UDP reorders and duplicates freely. Before this guard, an old ack
    reaching the drift resync rewound _next_state_id, which stalled
    input until the counter caught back up.
    """
    client = _client()
    client._next_state_id = 9
    client._unacked = [(n, b'\x00\x80\x80') for n in range(6, 9)]

    client._handle_state_ack(_ack(8))
    assert client._next_state_id == 9
    assert [n for n, _ in client._unacked] == [8]

    # Now an old ack arrives late.
    client._handle_state_ack(_ack(5))

    assert client._next_state_id == 9
    assert [n for n, _ in client._unacked] == [8]


def test_first_ack_after_connect_can_resync() -> None:
    """The drift resync still works on a fresh connection."""
    client = _client()
    client._next_state_id = 3
    client._unacked = [(n, b'\x00\x80\x80') for n in range(3)]
    client._last_ack = None

    client._handle_state_ack(_ack(200))

    assert not client._unacked
    assert client._next_state_id == 200


def test_dedupe_hosts_collapses_one_machine() -> None:
    """A host answering on loopback and its LAN address is one game.

    We broadcast to both, so the same host replies twice; listing it
    twice would look like two separate games.
    """
    from baremote._client import HostInfo, _dedupe_hosts

    hosts = [
        HostInfo(address='127.0.0.1', name='louptop'),
        HostInfo(address='192.168.29.70', name='louptop'),
    ]

    out = _dedupe_hosts(hosts)

    assert len(out) == 1
    # The routable address wins; it is the one that also works from
    # another device.
    assert out[0].address == '192.168.29.70'

    # Order of arrival must not matter.
    assert _dedupe_hosts(list(reversed(hosts)))[0].address == '192.168.29.70'


def test_dedupe_hosts_keeps_distinct_machines() -> None:
    """Different hosts stay separate."""
    from baremote._client import HostInfo, _dedupe_hosts

    out = _dedupe_hosts(
        [
            HostInfo(address='192.168.29.70', name='louptop'),
            HostInfo(address='192.168.29.81', name='other-box'),
        ]
    )
    assert [h.name for h in out] == ['louptop', 'other-box']


def test_menu_bit_round_trips() -> None:
    """A menu pulse is what the host reads as its start button.

    Guards the bit the app-mode sets when a single ui-request press is
    forwarded to the host instead of opening our own controls.
    """
    from baremote import _protocol

    state = RemoteState()
    state.set_button(_protocol.BUTTON_MENU, True)
    assert state.snapshot()[0] & _protocol.BUTTON_MENU

    state.set_button(_protocol.BUTTON_MENU, False)
    assert not state.snapshot()[0] & _protocol.BUTTON_MENU
