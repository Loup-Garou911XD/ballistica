# Released under the MIT License. See LICENSE for details.
#
"""Provides the Remote App-Subsystem."""

import uuid
import logging
from typing import TYPE_CHECKING, override

import babase

from baremote._state import RemoteState
from baremote._client import RemoteClient

if TYPE_CHECKING:
    pass

logger = logging.getLogger('ba.remote')


class RemoteAppSubsystem(babase.AppSubsystem):
    """Subsystem for Remote functionality in the app.

    Owns the controller state and the network client, so both control
    surfaces and the UI have one place to reach for them. The single
    shared instance is accessible as ``remote`` on the
    :class:`~babase.App` instance.
    """

    def __init__(self) -> None:
        super().__init__()

        #: Controller state both control surfaces write into.
        self.state = RemoteState()

        #: Speaks the protocol on a background thread.
        self.client = RemoteClient(self.state)

        self._started = False

    @property
    def player_name(self) -> str:
        """Name we present to hosts."""
        cfg = babase.app.config
        name = cfg.get('Remote Player Name')
        if isinstance(name, str) and name:
            return name
        return babase.app.env.device_name

    @player_name.setter
    def player_name(self, value: str) -> None:
        cfg = babase.app.config
        cfg['Remote Player Name'] = value
        cfg.commit()

    @property
    def client_tag(self) -> str:
        """Stable per-install id appended to our name.

        The host keys controller slots off the whole name string, so a
        stable tag is what makes a reconnect reuse our old slot rather
        than eat a second one out of the 24 available.
        """
        cfg = babase.app.config
        tag = cfg.get('Remote Client Tag')
        if not isinstance(tag, str) or not tag:
            tag = uuid.uuid4().hex[:8]
            cfg['Remote Client Tag'] = tag
            cfg.commit()
        return tag

    def start_client(self) -> None:
        """Bring the network client up if it isn't already."""
        if self._started:
            return
        self.client.start()
        self._started = True

    @override
    def on_app_shutdown(self) -> None:
        if self._started:
            self.client.stop()
            self._started = False
