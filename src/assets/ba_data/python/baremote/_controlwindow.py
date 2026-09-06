# Released under the MIT License. See LICENSE for details.
#
"""The widget control surface.

An on-screen gamepad built out of plain bauiv1 widgets. This exists
alongside the native control surface (keyboard / gamepad / the engine's
own touch controls) and is the one meant to be customized: subclass it
and override the ``create_*`` methods to lay the controls out
differently, and everything below -- state, protocol, networking --
keeps working unchanged.

Because this window sits on the screen stack, the engine treats a main-ui
as visible and stops routing input to our native delegate. So while this
window is up it is the only thing driving the controller; its 'Use
gamepad' button takes it off screen to hand control back to the native
surface, and a menu/start press brings it back.

One wrinkle worth knowing about: buttonwidget has no press/release pair,
only ``on_activate_call`` (which fires on release) and ``repeat``. So
held state is inferred -- each repeat tick pushes a deadline out, and the
button reads as released once that deadline passes.
"""

from typing import TYPE_CHECKING

import babase
import bauiv1 as bui

from baremote import _protocol

if TYPE_CHECKING:
    from typing import Callable

#: How long a button stays 'held' after its last repeat tick. Must
#: comfortably exceed the widget repeat interval or buttons will
#: stutter; too long and releases feel mushy.
HOLD_TIMEOUT = 0.15

#: State sampling rate. Matches the client's send rate.
_UPDATE_INTERVAL = 1.0 / 30.0


class ControlWindow(bui.Window):
    """On-screen controls driving the shared remote state."""

    def __init__(
        self,
        on_disconnect: Callable[[], None],
        on_hide: Callable[[], None],
    ) -> None:
        self._on_disconnect = on_disconnect
        self._on_hide = on_hide
        self._width, self._height = babase.get_virtual_screen_size()

        #: bit -> time at which it stops counting as held.
        self._held: dict[int, float] = {}

        #: direction name -> time at which it stops counting as held.
        self._dirs: dict[str, float] = {}

        #: Run is a latch rather than a hold. Set up here rather than in
        #: create_extras() so a subclass overriding that method doesn't
        #: have to remember to.
        self._run_latched = False
        self._run_button: bui.Widget | None = None

        super().__init__(
            root_widget=bui.containerwidget(
                size=(self._width, self._height),
                background=False,
            )
        )

        self.create_dpad()
        self.create_action_buttons()
        self.create_extras()

        self._timer: babase.AppTimer | None = babase.AppTimer(
            _UPDATE_INTERVAL, self._update, repeat=True
        )

    # ------------------------------------------------------- extension points

    def create_dpad(self) -> None:
        """Build the directional controls. Override to restyle."""
        cx = 180.0
        cy = 180.0
        size = (80.0, 80.0)

        self._dir_button((cx, cy + 85.0), size, 'Up', 'up')
        self._dir_button((cx, cy - 85.0), size, 'Down', 'down')
        self._dir_button((cx - 85.0, cy), size, 'Left', 'left')
        self._dir_button((cx + 85.0, cy), size, 'Right', 'right')

    def create_action_buttons(self) -> None:
        """Build the action buttons. Override to restyle."""
        cx = self._width - 180.0
        cy = 180.0
        size = (90.0, 90.0)

        self._hold_button((cx, cy - 90.0), size, 'Jump', _protocol.BUTTON_JUMP)
        self._hold_button((cx + 95.0, cy), size, 'Bomb', _protocol.BUTTON_BOMB)
        self._hold_button(
            (cx - 95.0, cy), size, 'Punch', _protocol.BUTTON_PUNCH
        )
        self._hold_button((cx, cy + 90.0), size, 'Grab', _protocol.BUTTON_THROW)

    def create_extras(self) -> None:
        """Build run / menu / disconnect. Override to restyle."""
        top = self._height - 60.0

        # Run can't be inferred from repeats the way the others can (you
        # hold it while doing other things), so it's a latch. A button
        # rather than a checkbox because checkboxwidget has no literal
        # flag for its label, which would send our plain text through
        # the resource-string path.
        self._run_button = bui.buttonwidget(
            parent=self._root_widget,
            position=(40.0, top),
            size=(140.0, 44.0),
            label='Run: off',
            text_literal=True,
            on_activate_call=self._toggle_run,
        )

        bui.buttonwidget(
            parent=self._root_widget,
            position=(self._width * 0.5 - 70.0, top),
            size=(140.0, 44.0),
            label='Menu',
            text_literal=True,
            on_activate_call=self._menu_press,
        )

        bui.buttonwidget(
            parent=self._root_widget,
            position=(self._width - 180.0, top),
            size=(140.0, 44.0),
            label='Disconnect',
            text_literal=True,
            on_activate_call=self._on_disconnect,
        )

        # Taking these controls off screen is what lets the native
        # surface work: the engine only routes input to our delegate
        # while no main-ui is visible. The menu/start button on a
        # gamepad brings them back.
        bui.buttonwidget(
            parent=self._root_widget,
            position=(self._width - 360.0, top),
            size=(160.0, 44.0),
            label='Use gamepad',
            text_literal=True,
            on_activate_call=self._on_hide,
        )

    # ----------------------------------------------------------------- public

    def close(self) -> None:
        """Tear the window down and release every held control."""
        self._timer = None
        self._held.clear()
        self._dirs.clear()
        self._run_latched = False
        babase.app.remote.state.reset()
        if self._root_widget:
            self._root_widget.delete()

    # ---------------------------------------------------------------- interna

    def _hold_button(
        self,
        position: tuple[float, float],
        size: tuple[float, float],
        label: str,
        bit: int,
    ) -> bui.Widget:
        return bui.buttonwidget(
            parent=self._root_widget,
            position=position,
            size=size,
            label=label,
            text_literal=True,
            repeat=True,
            enable_sound=False,
            on_activate_call=babase.Call(self._hold, bit),
        )

    def _dir_button(
        self,
        position: tuple[float, float],
        size: tuple[float, float],
        label: str,
        direction: str,
    ) -> bui.Widget:
        return bui.buttonwidget(
            parent=self._root_widget,
            position=position,
            size=size,
            label=label,
            text_literal=True,
            repeat=True,
            enable_sound=False,
            on_activate_call=babase.Call(self._hold_dir, direction),
        )

    def _hold(self, bit: int) -> None:
        self._held[bit] = babase.apptime() + HOLD_TIMEOUT

    def _hold_dir(self, direction: str) -> None:
        self._dirs[direction] = babase.apptime() + HOLD_TIMEOUT

    def _toggle_run(self) -> None:
        self._run_latched = not self._run_latched
        babase.app.remote.state.set_button(
            _protocol.BUTTON_RUN, self._run_latched
        )
        if self._run_button:
            onoff = 'on' if self._run_latched else 'off'
            bui.buttonwidget(
                edit=self._run_button,
                label=f'Run: {onoff}',
                text_literal=True,
            )

    def _menu_press(self) -> None:
        # A momentary tap; the host only cares about the edge.
        self._held[_protocol.BUTTON_MENU] = babase.apptime() + HOLD_TIMEOUT

    def _update(self) -> None:
        state = babase.app.remote.state
        now = babase.apptime()

        for bit in (
            _protocol.BUTTON_JUMP,
            _protocol.BUTTON_PUNCH,
            _protocol.BUTTON_BOMB,
            _protocol.BUTTON_THROW,
            _protocol.BUTTON_MENU,
        ):
            state.set_button(bit, self._held.get(bit, 0.0) > now)

        right = self._dirs.get('right', 0.0) > now
        left = self._dirs.get('left', 0.0) > now
        up = self._dirs.get('up', 0.0) > now
        down = self._dirs.get('down', 0.0) > now

        state.axis_h = (1.0 if right else 0.0) - (1.0 if left else 0.0)
        state.axis_v = (1.0 if up else 0.0) - (1.0 if down else 0.0)
