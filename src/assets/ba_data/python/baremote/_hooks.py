# Released under the MIT License. See LICENSE for details.
#
"""Snippets of code for use by the native layer."""

import babase


def handle_input_command(input_type: int, value: float) -> None:
    """Called by our native input delegate for every input event.

    Logic thread only. Kept deliberately tiny -- this is on the path of
    every axis wiggle from every attached device.
    """
    from baremote import _nativecontrols

    _nativecontrols.apply_input(babase.app.remote.state, input_type, value)


def request_main_ui() -> None:
    """Called by the native layer when input asks for a ui.

    Reached when a device sends a menu/start press with nothing on
    screen -- which, with the controls hidden so native input can flow,
    is the player's only route back.
    """
    from baremote._appmode import RemoteAppMode

    mode = babase.app.mode
    if isinstance(mode, RemoteAppMode):
        mode.show_ui()
