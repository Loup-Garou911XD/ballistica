# Released under the MIT License. See LICENSE for details.
#
"""Snippets of code for use by the native layer."""

import babase

from baremote._nativecontrols import apply_input


def handle_input_command(input_type: int, value: float) -> None:
    """Called by our native input delegate for every input event.

    Logic thread only. Kept deliberately tiny -- this is on the path of
    every axis wiggle from every attached device, which is also why the
    import above is module-level rather than in here.
    """
    apply_input(babase.app.remote.state, input_type, value)


def request_main_ui(from_controller: bool) -> None:
    """Called by the native layer when input asks for a ui.

    Reached when escape or a menu/start press arrives with nothing on
    screen. ``from_controller`` separates the two: a gamepad's start
    button is the host's pause button, while escape is a 'back' aimed at
    our own ui.
    """
    from baremote._appmode import RemoteAppMode

    mode = babase.app.mode
    if isinstance(mode, RemoteAppMode):
        mode.on_request_main_ui(from_controller)
