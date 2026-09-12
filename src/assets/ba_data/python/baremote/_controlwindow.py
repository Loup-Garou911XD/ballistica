# Released under the MIT License. See LICENSE for details.
#
"""The widget overlay.

Playing happens on the engine's own natively drawn controls -- a floating
analog stick plus four action buttons, see ``base::TouchInput``. This
window is the overlay you get on top of those: run, menu, disconnect, and
the way back to playing. Escape toggles between the two.

Steering and the action buttons deliberately do *not* live here. A
buttonwidget has no press/release pair and no drag, only
``on_activate_call`` (which fires on release) and ``repeat`` -- so a
widget d-pad can only ever be digital, with held state inferred from
repeat ticks. The native stick does real analog aim and true
press/release, so it owns those.

What remains here is the customization point: subclass and override
:meth:`~ControlWindow.create_extras` to lay the overlay out differently,
and everything below -- state, protocol, networking -- keeps working
unchanged. A subclass that wants momentary controls back can wire a
``repeat=True`` button to ``on_activate_call=babase.CallStrict(self._hold,
bit)``; :meth:`~ControlWindow._update` samples those deadlines at 30hz.

Because this window sits on the screen stack, the engine treats a main-ui
as visible and stops routing input to our native delegate -- which also
takes the native controls off screen. So the two surfaces are never up at
once.

Every control here is non-selectable on purpose. Mouse and touch still
work (button hit-testing keys off 'enabled', not 'selectable'), but the
controls stay out of gamepad/keyboard navigation -- otherwise a start
press would activate whichever one happened to be selected, and hitting
'Use joystick' or 'Disconnect' by accident is exactly the close/reopen
flicker this surface must not have. A gamepad's only interactions here
are cancel (hide) and start (already handled by the engine).
"""

from typing import TYPE_CHECKING

import babase
import bauiv1 as bui

from baremote import _protocol

if TYPE_CHECKING:
    from typing import Callable

#: How long a control stays 'held' after its last activation.
#:
#: ButtonWidget repeats on a 0.3s timer (see button_widget.cc), so a
#: repeating control needs this to clear that interval or a genuinely
#: held button reads as released between ticks and stutters. Menu is the
#: only user of it in this layout -- a tap the host sees as one edge --
#: but a subclass adding repeating controls depends on the margin.
HOLD_TIMEOUT = 0.45

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

        #: protocol button bit -> time it stops counting as held.
        self._deadlines: dict[int, float] = {}

        #: Run is a latch rather than a hold. Set up here rather than in
        #: create_extras() so a subclass overriding that method doesn't
        #: have to remember to.
        self._run_latched = False
        self._run_button: bui.Widget | None = None

        super().__init__(
            root_widget=bui.containerwidget(
                size=(self._width, self._height),
                background=False,
                # Claim cancel ourselves. Left unhandled it walks up to
                # ui_v1's global back button, which bounces through
                # RootWidget::BackPress and back down as another cancel
                # -- with nothing here to catch it the result is an
                # unpredictable close/reopen rather than a decision.
                # Back means 'switch to the gamepad surface'.
                on_cancel_call=self._on_hide,
            )
        )

        self.create_extras()

        self._timer: babase.AppTimer | None = babase.AppTimer(
            _UPDATE_INTERVAL, self._update, repeat=True
        )

    # ------------------------------------------------------- extension points

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
            selectable=False,
            on_activate_call=self._toggle_run,
        )

        bui.buttonwidget(
            parent=self._root_widget,
            position=(self._width * 0.5 - 70.0, top),
            size=(140.0, 44.0),
            label='Menu',
            text_literal=True,
            selectable=False,
            # A momentary tap; the host only cares about the edge.
            on_activate_call=babase.CallStrict(
                self._hold, _protocol.BUTTON_MENU
            ),
        )

        bui.buttonwidget(
            parent=self._root_widget,
            position=(self._width - 180.0, top),
            size=(140.0, 44.0),
            label='Disconnect',
            text_literal=True,
            selectable=False,
            on_activate_call=self._on_disconnect,
        )

        # Taking these controls off screen is what lets the native
        # surface work: the engine only routes input to our delegate --
        # and only draws its own stick and action buttons -- while no
        # main-ui is visible. Escape brings us back.
        #
        # Note for anyone driving the *host's* menus from here: Bomb is
        # what goes back over there. The host turns our bomb bit into a
        # widget cancel; our Menu button becomes a start, which opens
        # and pauses rather than backs out.
        bui.buttonwidget(
            parent=self._root_widget,
            position=(self._width - 380.0, top),
            size=(180.0, 44.0),
            label='Use joystick (esc)',
            text_literal=True,
            selectable=False,
            on_activate_call=self._on_hide,
        )

    # ----------------------------------------------------------------- public

    def close(self) -> None:
        """Tear the window down and release every held control."""
        self._timer = None
        self._deadlines.clear()
        self._run_latched = False
        babase.app.remote.state.reset()
        if self._root_widget:
            self._root_widget.delete()

    # ---------------------------------------------------------------- interna

    def _hold(self, bit: int) -> None:
        self._deadlines[bit] = babase.apptime() + HOLD_TIMEOUT

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

    def _update(self) -> None:
        state = babase.app.remote.state
        now = babase.apptime()

        # Menu is the only one of these this layout can hold. The rest
        # are listed so that anything the *native* controls left pressed
        # gets released: the engine stops routing input to them the
        # moment we go up, so they never get to send the release
        # themselves and the host would otherwise see the button stuck.
        for bit in (
            _protocol.BUTTON_JUMP,
            _protocol.BUTTON_PUNCH,
            _protocol.BUTTON_BOMB,
            _protocol.BUTTON_THROW,
            _protocol.BUTTON_MENU,
        ):
            state.set_button(bit, self._deadlines.get(bit, 0.0) > now)

        # Same reasoning for aim: nothing here steers, so hold it neutral
        # rather than letting the stick's last reading walk the character
        # around while this window is up.
        state.axis_h = 0.0
        state.axis_v = 0.0
