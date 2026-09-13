# Released under the MIT License. See LICENSE for details.
#
"""The native control surface.

Turns engine input events into controller state. Everything the engine
knows how to read -- keyboard, SDL gamepads, and its own on-screen touch
controls -- arrives here through a single InputDeviceDelegate hook in our
native layer, already in a press/release vocabulary that lines up with
the wire format.

Note that these events only reach us while no bauiv1 window is on screen;
with a main-ui up the engine routes input to widget navigation instead.
That is what makes this surface and the widget one alternatives rather
than simultaneous.
"""

from typing import TYPE_CHECKING

from babase import InputType

from baremote import _protocol

if TYPE_CHECKING:
    from baremote._state import RemoteState

#: Press/release event pairs and the button bit each drives.
_BUTTON_EVENTS: dict[InputType, tuple[int, bool]] = {
    InputType.JUMP_PRESS: (_protocol.BUTTON_JUMP, True),
    InputType.JUMP_RELEASE: (_protocol.BUTTON_JUMP, False),
    InputType.PUNCH_PRESS: (_protocol.BUTTON_PUNCH, True),
    InputType.PUNCH_RELEASE: (_protocol.BUTTON_PUNCH, False),
    InputType.BOMB_PRESS: (_protocol.BUTTON_BOMB, True),
    InputType.BOMB_RELEASE: (_protocol.BUTTON_BOMB, False),
    InputType.PICK_UP_PRESS: (_protocol.BUTTON_THROW, True),
    InputType.PICK_UP_RELEASE: (_protocol.BUTTON_THROW, False),
    InputType.START_PRESS: (_protocol.BUTTON_MENU, True),
    InputType.START_RELEASE: (_protocol.BUTTON_MENU, False),
    InputType.HOLD_POSITION_PRESS: (_protocol.BUTTON_HOLD_POSITION, True),
    InputType.HOLD_POSITION_RELEASE: (_protocol.BUTTON_HOLD_POSITION, False),
}

#: Below this, a run axis counts as not held.
_RUN_THRESHOLD = 0.1


def apply_input(state: RemoteState, input_type: int, value: float) -> None:
    """Fold one engine input event into ``state``.

    Called from the native layer on the logic thread with the raw
    :class:`~babase.InputType` value.
    """
    try:
        itype = InputType(input_type)
    except ValueError:
        # Unknown event; newer engine than we know about.
        return

    button = _BUTTON_EVENTS.get(itype)
    if button is not None:
        bit, pressed = button
        state.set_button(bit, pressed)
        return

    if itype is InputType.LEFT_RIGHT:
        state.axis_h = value
    elif itype is InputType.UP_DOWN:
        state.axis_v = value
    elif itype is InputType.RUN:
        # Run arrives as a continuous value (triggers are analog), but
        # the wire only has a bit for it.
        state.set_button(_protocol.BUTTON_RUN, value > _RUN_THRESHOLD)

    # FLY_PRESS/RELEASE arrive alongside jump on every gamepad, and the
    # host never decodes the fly bit, so there is nothing to do with
    # them. Directional *_PRESS/_RELEASE events are UI navigation only.
