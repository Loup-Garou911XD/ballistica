# Released under the MIT License. See LICENSE for details.
#
"""Provides the remote-control app-mode."""

import logging
from typing import TYPE_CHECKING, override

import _baremote
import babase
import bauiv1 as bui

from baremote._client import ConnectionState
from baremote._uiassets import make_ui_asset_set

if TYPE_CHECKING:
    from babase import AppIntent, AppModeConfig

    from baremote._scanwindow import ScanWindow
    from baremote._controlwindow import ControlWindow

logger = logging.getLogger('ba.remote')


class RemoteAppModeConfig(babase.AppModeConfig):
    """Config for a run of :class:`RemoteAppMode`.

    Amendable before activation, so a plugin can restyle the ui by
    reassigning slots on :attr:`ui_assets`.
    """

    def __init__(self) -> None:
        self.ui_assets = make_ui_asset_set()


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
        assert isinstance(intent, babase.AppIntentDefault)
        _baremote.remote_app_mode_handle_app_intent_default()

    @override
    def new_app_mode_config(self) -> AppModeConfig:
        return RemoteAppModeConfig()

    @override
    def on_activate(self, config: AppModeConfig) -> None:
        assert isinstance(config, RemoteAppModeConfig)

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

        _baremote.remote_app_mode_deactivate()

    # ----------------------------------------------------------------- public

    def show_ui(self) -> None:
        """Put a window back on screen.

        Whichever one matches where we are: the controls if we have a
        host, the scan list if we don't.
        """
        if self._scan_window is not None or self._control_window is not None:
            return

        if (
            babase.app.remote.client.connection_state
            is ConnectionState.CONNECTED
        ):
            self._show_control_window()
        else:
            self._show_scan_window()

    def hide_controls(self) -> None:
        """Take the controls off screen so native input can flow.

        The engine routes input to widget navigation whenever a main-ui
        is visible, so an empty screen is the precondition for the
        keyboard/gamepad/touch path working at all. The menu button
        brings the controls back via
        :meth:`~babase.AppMode.RequestMainUI`.
        """
        self._close_windows()

    # ---------------------------------------------------------------- interna

    def _close_windows(self) -> None:
        if self._scan_window is not None:
            self._scan_window.close()
            self._scan_window = None
        if self._control_window is not None:
            self._control_window.close()
            self._control_window = None

    def _show_scan_window(self) -> None:
        from baremote._scanwindow import ScanWindow

        self._close_windows()
        self._scan_window = ScanWindow()

    def _show_control_window(self) -> None:
        from baremote._controlwindow import ControlWindow

        self._close_windows()
        self._control_window = ControlWindow(
            on_disconnect=self._disconnect, on_hide=self.hide_controls
        )

    def _on_connected(self) -> None:
        self._show_control_window()

    def _on_disconnected(self, reason: str | None) -> None:
        babase.app.remote.state.reset()

        was_connected = self._control_window is not None
        self._show_scan_window()

        if reason is not None:
            assert self._scan_window is not None
            self._scan_window.set_status(reason)
        elif was_connected:
            assert self._scan_window is not None
            self._scan_window.set_status('Disconnected.')

    def _disconnect(self) -> None:
        babase.app.remote.client.disconnect()
        babase.app.remote.state.reset()
        self._show_scan_window()
