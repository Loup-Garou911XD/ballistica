# Released under the MIT License. See LICENSE for details.
#
"""Shared controller state.

Both control surfaces (the native input path and the widget path) write
into one of these, and the client samples it. Keeping them behind a
single small object is what lets the protocol layer stay unaware of
which surface is driving.
"""

from baremote import _protocol


class RemoteState:
    """The current controller state, as button bits plus two axes."""

    def __init__(self) -> None:
        self.buttons = 0

        #: Aim, in player-facing terms: +1 is right and +1 is up. The
        #: wire wants vertical the other way round, but that flip lives
        #: in :meth:`snapshot` so neither control surface has to think
        #: about it.
        self.axis_h = 0.0
        self.axis_v = 0.0

    def set_button(self, bit: int, pressed: bool) -> None:
        """Set or clear a single button bit."""
        if pressed:
            self.buttons |= bit
        else:
            self.buttons &= ~bit

    def reset(self) -> None:
        """Drop everything back to neutral."""
        self.buttons = 0
        self.axis_h = 0.0
        self.axis_v = 0.0

    def snapshot(self) -> bytes:
        """Encode the current state as a 3-byte wire entry.

        Vertical is negated here. The host turns our byte back into a
        synthetic joystick axis event, and JoystickInput inverts the
        vertical axis on the way to InputType.UP_DOWN (see
        joystick_input.cc). Sending our up-positive value as-is would
        come out upside down at the far end.
        """
        return _protocol.pack_state(self.buttons, self.axis_h, -self.axis_v)
