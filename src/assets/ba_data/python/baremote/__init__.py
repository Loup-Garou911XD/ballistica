# Released under the MIT License. See LICENSE for details.
#
"""Remote-control app functionality.

Lets the engine act as a game controller for a BombSquad host on the
local network, speaking the same UDP protocol as the standalone
BombSquad Remote apps.
"""

# ba_meta require api 9

# Package up various private bits into a nice clean public API.
from baremote._appmode import RemoteAppMode, RemoteAppModeConfig
from baremote._appsubsystem import RemoteAppSubsystem
from baremote._client import ConnectionState, HostInfo, RemoteClient
from baremote._controlwindow import ControlWindow
from baremote._scanwindow import ScanWindow
from baremote._state import RemoteState

__all__ = [
    'ConnectionState',
    'ControlWindow',
    'HostInfo',
    'RemoteAppMode',
    'RemoteAppModeConfig',
    'RemoteAppSubsystem',
    'RemoteClient',
    'RemoteState',
    'ScanWindow',
]
