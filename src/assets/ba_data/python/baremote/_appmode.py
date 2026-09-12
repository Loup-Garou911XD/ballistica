# Released under the MIT License. See LICENSE for details.
#
"""Provides the remote-control app-mode."""

from typing import TYPE_CHECKING, override

import _baremote
import babase
import bauiv1 as bui

from baremote import _protocol
from baremote._client import ConnectionState
from baremote._uiassets import make_ui_asset_set
from baremote._baseassets import make_base_asset_set
from baremote._scanwindow import ScanWindow
from baremote._controlwindow import ControlWindow

if TYPE_CHECKING:
    from babase import AppIntent, AppModeConfig

class RemoteAppModeConfig(babase.AppModeConfig):
    """Config for a run of :class:`RemoteAppMode`.

    Amendable before activation, so a plugin can restyle the ui by
    reassigning slots on :attr:`ui_assets`.
    """

    def __init__(self) -> None:
        self.ui_assets = make_ui_asset_set()
        self.base_assets = make_base_asset_set()


# ba_meta export babase.AppMode
class RemoteAppMode(babase.AppMode):
    """Turns the app into a game controller for a BombSquad host.

    Speaks the same UDP protocol as the standalone BombSquad Remote apps,
    so any host on the local network accepts us as a controller.
    """

    def __init__(self) -> None:
        super().__init__()
        self._scan_window: ScanWindow | None = None
        self._control_window: ControlWindow | None = None

    @override
    @classmethod
    def can_handle_intent(cls, intent: AppIntent) -> bool:
        # Same set EmptyAppMode handles.
        return isinstance(
            intent, babase.AppIntentExec | babase.AppIntentDefault
        )

    @override
    def handle_intent(self, intent: AppIntent) -> None:
        if isinstance(intent, babase.AppIntentExec):
            _baremote.remote_app_mode_handle_app_intent_exec(intent.code)
            return
        # Nothing to do for a default intent; on_activate already brought
        # our ui up.
        assert isinstance(intent, babase.AppIntentDefault)

    @override
    def new_app_mode_config(self) -> AppModeConfig:
        return RemoteAppModeConfig()

    @override
    def on_activate(self, config: AppModeConfig) -> None:
        assert isinstance(config, RemoteAppModeConfig)

        # Art for base's own draws -- for us that means the engine's
        # on-screen action buttons, which are our main control surface.
        babase.set_base_asset_set(config.base_assets)

        # Hand ui_v1 the assets its widgets draw themselves with. This
        # has to land *before* the native activate below, which is what
        # registers ui_v1 as the ui-delegate and builds the root widget
        # from this set. Activating without it disables the ui outright.
        bui.set_ui_asset_set(config.ui_assets)

        # Let the native layer set itself as the app-mode and hand ui_v1
        # the ui-delegate job. Nothing draws until this happens.
        _baremote.remote_app_mode_activate()

        subsystem = babase.app.remote
        subsystem.start_client()
        subsystem.client.on_connected = self._on_connected
        subsystem.client.on_disconnected = self._on_disconnected

        self._show_scan_window()

    @override
    def on_deactivate(self) -> None:
        subsystem = babase.app.remote
        subsystem.client.on_connected = None
        subsystem.client.on_disconnected = None
        subsystem.client.disconnect()

        self._close_windows()

    # ----------------------------------------------------------------- public

    def on_request_main_ui(self, from_controller: bool) -> None:
        """A device asked for a ui while none was on screen.

        Escape and a gamepad's start button both arrive here, and they
        mean opposite things. Start is the host's pause button, so we
        forward it -- there would otherwise be no way to pause a game
        from the gamepad surface. Escape is a back press aimed at *our*
        ui, so it brings our controls up locally and the host never
        hears about it.

        Escape must not be forwarded as a menu press: the host maps our
        menu bit to a gamepad start, and a start with a menu already
        open means "activate the selected widget" over there
        (JoystickInput sends WidgetMessage::Type::kStart). Pressing it
        repeatedly just toggles in and out of whatever happens to be
        selected. Going *back* in a host menu is the bomb button, which
        the host turns into a cancel.
        """
        client = babase.app.remote.client
        if (
            not from_controller
            or self._have_ui()
            or client.connection_state is not ConnectionState.CONNECTED
        ):
            self.show_ui()
            return

        self.pulse_menu()

    def pulse_menu(self) -> None:
        """Send the host a momentary menu press."""
        state = babase.app.remote.state
        state.set_button(_protocol.BUTTON_MENU, True)

        def _release() -> None:
            state.set_button(_protocol.BUTTON_MENU, False)

        # Long enough for the press and the release to each land in a
        # state packet at our 30hz send rate.
        babase.apptimer(0.15, _release)

    def show_ui(self) -> None:
        """Put a window back on screen.

        Whichever one matches where we are: the controls if we have a
        host, the scan list if we don't.
        """
        if self._have_ui():
            return

        if (
            babase.app.remote.client.connection_state
            is ConnectionState.CONNECTED
        ):
            self._show_control_window()
        else:
            self._show_scan_window()

    def hide_controls(self) -> None:
        """Take our widgets off screen so native input can flow.

        The engine routes input to widget navigation whenever a main-ui
        is visible, so an empty screen is the precondition for the
        native path working at all. That path is both the engine's
        on-screen stick and action buttons (which likewise only draw
        with no main-ui up) and any keyboard or gamepad attached. The
        menu button brings our widgets back via
        :meth:`~babase.AppMode.RequestMainUI`.
        """
        self._close_windows()

    # ---------------------------------------------------------------- interna

    def _have_ui(self) -> bool:
        return (
            self._scan_window is not None or self._control_window is not None
        )

    def _close_windows(self) -> None:
        if self._scan_window is not None:
            self._scan_window.close()
            self._scan_window = None
        if self._control_window is not None:
            self._control_window.close()
            self._control_window = None

    def _show_scan_window(self) -> None:
        self._close_windows()
        self._scan_window = ScanWindow()

    def _show_control_window(self) -> None:
        self._close_windows()
        self._control_window = ControlWindow(
            on_disconnect=self._disconnect, on_hide=self.hide_controls
        )

    def _on_connected(self) -> None:
        # Straight to the engine's own on-screen controls: a floating
        # analog stick plus the four action buttons, drawn natively by
        # base::TouchInput. They only appear while no widget is on
        # screen, so getting there means taking our own ui down.
        #
        # A screen-message is safe to leave up here -- base draws those
        # itself, so unlike a widget it does not count as a main-ui and
        # does not switch the controls back off.
        babase.screenmessage(
            'Connected. Press escape twice for the menu.', literal=True
        )
        self.hide_controls()

    def _on_disconnected(self, reason: str | None) -> None:
        babase.app.remote.state.reset()

        status = reason or (
            'Disconnected.' if self._control_window is not None else None
        )
        self._show_scan_window()

        if status is not None:
            assert self._scan_window is not None
            self._scan_window.set_status(status)

    def _disconnect(self) -> None:
        babase.app.remote.client.disconnect()
        babase.app.remote.state.reset()
        self._show_scan_window()
