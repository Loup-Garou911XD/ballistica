# Released under the MIT License. See LICENSE for details.
#
"""Tests for the remote-app wire protocol.

These assert byte-exact layouts against what the host side
(``src/ballistica/base/input/support/remote_app_server.cc``) parses. No
engine binary is needed -- baremote._protocol is deliberately free of
sockets and engine imports.
"""

import struct

from baremote import _protocol


def test_game_query_is_a_single_byte() -> None:
    """Discovery is one bare packet-type byte."""
    assert _protocol.pack_game_query() == b'\x08'


def test_parse_game_response() -> None:
    """Host name comes back after the type byte."""
    assert _protocol.parse_game_response(b'\x09Some Machine') == 'Some Machine'

    # The host builds the reply in a fixed buffer, so trailing NULs show up.
    assert _protocol.parse_game_response(b'\x09Foo\x00\x00') == 'Foo'

    # Wrong type or empty gets rejected rather than mis-parsed.
    assert _protocol.parse_game_response(b'\x08') is None
    assert _protocol.parse_game_response(b'') is None


def test_id_request_layout() -> None:
    """Handshake matches the host's five-byte header plus name."""
    name = _protocol.encode_name('Bob', 'abcd1234')
    packet = _protocol.pack_id_request(0x1234, name)

    assert packet[0] == _protocol.PACKET_ID_REQUEST
    assert packet[1] == 121  # kRemoteAppProtocolVersion

    # request-id is a native-endian int16 (memcpy'd on the far side).
    assert struct.unpack('<h', packet[2:4])[0] == 0x1234

    # 50 is the 'I want 24-bit states' request.
    assert packet[4] == 50
    assert packet[5:] == b'Bob#abcd1234'

    # The host rejects anything outside this range outright.
    assert 5 <= len(packet) <= 127


def test_encode_name_truncates_on_char_boundary() -> None:
    """Over-long names get cut without splitting a codepoint."""
    encoded = _protocol.encode_name('é' * 80)
    assert len(encoded) <= _protocol.MAX_NAME_BYTES

    # Must still be decodable; a naive byte slice would split one of the
    # two-byte characters.
    encoded.decode('utf-8')


def test_parse_id_response() -> None:
    """Accept packet yields client id and protocol response."""
    assert _protocol.parse_id_response(b'\x03\x07\x64') == (7, 100)
    assert _protocol.parse_id_response(b'\x04\x02') is None


def test_parse_disconnect() -> None:
    """Host disconnect carries a reason code."""
    assert (
        _protocol.parse_disconnect(b'\x04\x02')
        is _protocol.RemoteError.NOT_ACCEPTING_CONNECTIONS
    )
    assert _protocol.parse_disconnect(b'\x04\xff') is None
    assert _protocol.parse_disconnect(b'\x03\x00\x64') is None


def test_axis_quantization() -> None:
    """Axis bytes round-trip through the host's decode formula."""
    assert _protocol.axis_byte(-1.0) == 0
    assert _protocol.axis_byte(1.0) == 255

    # Exact centre is not representable; 128 is the closest we get.
    assert _protocol.axis_byte(0.0) == 128

    # Out-of-range input clamps rather than wrapping.
    assert _protocol.axis_byte(-5.0) == 0
    assert _protocol.axis_byte(5.0) == 255

    # Every byte we can emit decodes back to within half a step.
    for value in (-1.0, -0.5, 0.0, 0.25, 1.0):
        raw = _protocol.axis_byte(value)
        decoded = -1.0 + 2.0 * (raw / 255.0)
        assert abs(decoded - value) < 0.005


def test_state_packet_framing() -> None:
    """Host validates length as exactly 4 + count*3."""
    states = [
        _protocol.pack_state(_protocol.BUTTON_JUMP, 0.0, 0.0),
        _protocol.pack_state(0, 1.0, -1.0),
    ]
    packet = _protocol.pack_state_packet(3, 250, states)

    assert packet[0] == _protocol.PACKET_STATE2
    assert packet[1] == 3  # client id
    assert packet[2] == 2  # state count
    assert packet[3] == 250  # starting state id
    assert len(packet) == 4 + 2 * 3

    # Per-state layout: buttons, then the two axis bytes.
    assert packet[4] == _protocol.BUTTON_JUMP
    assert packet[5] == 128
    assert packet[6] == 128
    assert packet[7] == 0
    assert packet[8] == 255
    assert packet[9] == 0


def test_state_packet_wraps_start_id() -> None:
    """State ids are a single byte and wrap."""
    packet = _protocol.pack_state_packet(0, 256 + 5, [b'\x00\x80\x80'])
    assert packet[3] == 5


def test_parse_state_ack() -> None:
    """Ack reports the next state id the host wants."""
    assert _protocol.parse_state_ack(b'\x06\x2a') == 42
    assert _protocol.parse_state_ack(b'\x05\x2a') is None


def test_disconnect_round_trip() -> None:
    """Goodbye packet and its ack."""
    assert _protocol.pack_disconnect(9) == b'\x04\x09'
    assert _protocol.is_disconnect_ack(b'\x07')
    assert not _protocol.is_disconnect_ack(b'\x06\x00')
