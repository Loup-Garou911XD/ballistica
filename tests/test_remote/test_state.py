# Released under the MIT License. See LICENSE for details.
#
"""Tests for the shared controller state."""

from baremote import _protocol
from baremote._state import RemoteState


def test_button_bits() -> None:
    """Bits set and clear independently."""
    state = RemoteState()
    assert state.buttons == 0

    state.set_button(_protocol.BUTTON_JUMP, True)
    state.set_button(_protocol.BUTTON_PUNCH, True)
    assert state.buttons == _protocol.BUTTON_JUMP | _protocol.BUTTON_PUNCH

    state.set_button(_protocol.BUTTON_JUMP, False)
    assert state.buttons == _protocol.BUTTON_PUNCH


def test_snapshot_inverts_vertical() -> None:
    """Vertical is flipped on the way to the wire.

    The host feeds our byte back through JoystickInput, which inverts the
    vertical axis; sending our up-positive value unflipped would arrive
    upside down.
    """
    state = RemoteState()
    state.axis_v = 1.0  # Player-facing 'up'.

    snapshot = state.snapshot()
    assert snapshot[2] == _protocol.axis_byte(-1.0)

    # Horizontal passes through untouched.
    state.axis_v = 0.0
    state.axis_h = 1.0
    assert state.snapshot()[1] == _protocol.axis_byte(1.0)


def test_reset() -> None:
    """Reset drops everything back to neutral."""
    state = RemoteState()
    state.set_button(_protocol.BUTTON_BOMB, True)
    state.axis_h = 1.0
    state.axis_v = -1.0

    state.reset()

    assert state.buttons == 0
    assert state.snapshot() == bytes([0, 128, 128])
