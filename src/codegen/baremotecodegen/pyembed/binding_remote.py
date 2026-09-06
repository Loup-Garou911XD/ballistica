# Released under the MIT License. See LICENSE for details.

# Where most of our python-c++ binding happens.
# Python objects should be added here along with their associated c++ enum.
# pylint: disable=useless-suppression, missing-module-docstring, line-too-long

from baremote import _hooks

# The C++ layer looks for this variable:
values = [
    _hooks.handle_input_command,  # kHandleInputCommandCall
    _hooks.request_main_ui,  # kRequestMainUICall
]
