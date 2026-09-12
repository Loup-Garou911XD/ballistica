# Released under the MIT License. See LICENSE for details.
#
"""Window for finding and connecting to a host."""

from typing import TYPE_CHECKING, cast

import babase
import bauiv1 as bui

if TYPE_CHECKING:
    from baremote._client import HostInfo


class ScanWindow(bui.Window):
    """Lists hosts found on the local network and connects to one."""

    def __init__(self) -> None:
        self._width, self._height = babase.get_virtual_screen_size()

        super().__init__(
            root_widget=bui.containerwidget(
                size=(self._width, self._height),
                background=False,
                # Claim cancel rather than letting it walk up to ui_v1's
                # global back button. This is the app's root screen, so
                # back has nowhere to go -- but leaving the message
                # unclaimed makes it bounce around the root widget with
                # visible side effects.
                on_cancel_call=self._on_cancel,
            )
        )

        subsystem = babase.app.remote

        cx = self._width * 0.5
        top = self._height - 60.0

        bui.textwidget(
            parent=self._root_widget,
            position=(cx - 200.0, top),
            size=(400.0, 40.0),
            text='BombSquad Remote',
            h_align='center',
            v_align='center',
            scale=1.3,
            maxwidth=380.0,
            literal=True,
        )

        bui.textwidget(
            parent=self._root_widget,
            position=(cx - 300.0, top - 60.0),
            size=(120.0, 40.0),
            text='Your name:',
            h_align='right',
            v_align='center',
            literal=True,
        )
        self._name_field = bui.textwidget(
            parent=self._root_widget,
            position=(cx - 170.0, top - 60.0),
            size=(300.0, 40.0),
            text=subsystem.player_name,
            editable=True,
            max_chars=24,
            autoselect=True,
        )

        # Host list.
        self._scroll = bui.scrollwidget(
            parent=self._root_widget,
            position=(cx - 250.0, top - 300.0),
            size=(500.0, 220.0),
        )
        self._column = bui.columnwidget(parent=self._scroll, border=2, margin=0)

        self._status = bui.textwidget(
            parent=self._root_widget,
            position=(cx - 250.0, top - 340.0),
            size=(500.0, 30.0),
            text='Scanning for games on your network...',
            h_align='center',
            v_align='center',
            scale=0.8,
            color=(0.7, 0.7, 0.7),
            literal=True,
        )

        # Manual entry, for anything broadcast can't reach.
        bui.textwidget(
            parent=self._root_widget,
            position=(cx - 300.0, top - 400.0),
            size=(120.0, 40.0),
            text='Address:',
            h_align='right',
            v_align='center',
            literal=True,
        )
        self._address_field = bui.textwidget(
            parent=self._root_widget,
            position=(cx - 170.0, top - 400.0),
            size=(300.0, 40.0),
            text='',
            editable=True,
            max_chars=64,
        )
        bui.buttonwidget(
            parent=self._root_widget,
            position=(cx + 140.0, top - 402.0),
            size=(140.0, 44.0),
            label='Connect',
            text_literal=True,
            on_activate_call=self._connect_manual,
        )

        self._host_buttons: list[bui.Widget] = []

        subsystem.client.on_hosts_changed = self._on_hosts_changed
        subsystem.client.set_scanning(True)

    def _on_cancel(self) -> None:
        """Back on the root screen: nothing to go back to."""

    def close(self) -> None:
        """Tear the window down and stop scanning."""
        subsystem = babase.app.remote
        subsystem.client.on_hosts_changed = None
        subsystem.client.set_scanning(False)
        if self._root_widget:
            self._root_widget.delete()

    def set_status(self, text: str) -> None:
        """Show a message under the host list."""
        if self._status:
            bui.textwidget(edit=self._status, text=text, literal=True)

    def _current_name(self) -> str:
        name = _query_text(self._name_field).strip()
        return name if name else babase.app.env.device_name

    def _on_hosts_changed(self, hosts: list[HostInfo]) -> None:
        if not self._column:
            return

        for btn in self._host_buttons:
            if btn:
                btn.delete()
        self._host_buttons = []

        for host in hosts:
            self._host_buttons.append(
                bui.buttonwidget(
                    parent=self._column,
                    size=(460.0, 44.0),
                    label=f'{host.name}  ({host.address})',
                    text_literal=True,
                    on_activate_call=babase.CallStrict(
                        self._connect, host.address
                    ),
                )
            )

        if hosts:
            self.set_status('Choose a game to connect to.')
        else:
            self.set_status('Scanning for games on your network...')

    def _connect_manual(self) -> None:
        address = _query_text(self._address_field).strip()
        if not address:
            self.set_status('Enter an address first.')
            return
        self._connect(address)

    def _connect(self, address: str) -> None:
        subsystem = babase.app.remote
        name = self._current_name()
        subsystem.player_name = name
        subsystem.client.set_scanning(False)
        subsystem.client.connect(address, name, subsystem.client_tag)
        self.set_status(f'Connecting to {address}...')


def _query_text(widget: bui.Widget) -> str:
    """Read an editable textwidget's current contents.

    textwidget's 'query' form returns a str at runtime but is typed as
    returning a Widget like every other form, so a cast is needed. Doing
    it here keeps it off the call sites (same approach bauiv1lib takes).
    """
    if not widget:
        return ''
    return cast(str, bui.textwidget(query=widget))
