# Released under the MIT License. See LICENSE for details.
#
"""Plugin Settings UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ba
from bastd.ui.config import ConfigCheckBox

if TYPE_CHECKING:
    pass

class PluginSettingsWindow(ba.Window):
    """Plugin Settings Window"""

    def __init__(
        self,
        transition: str = 'in_right'
    ):

        scale_origin: tuple[float, float] | None
        self._transition_out = 'out_right'
        scale_origin = None

        uiscale = ba.app.ui.uiscale
        width = 470.0 if uiscale is ba.UIScale.SMALL else 470.0
        height = (
            365.0
            if uiscale is ba.UIScale.SMALL
            else 300.0
            if uiscale is ba.UIScale.MEDIUM
            else 370.0
        )
        top_extra = 10 if uiscale is ba.UIScale.SMALL else 0

        super().__init__(
            root_widget=ba.containerwidget(
                size=(width, height + top_extra),
                transition=transition,
                toolbar_visibility='menu_minimal',
                scale_origin_stack_offset=scale_origin,
                scale=(
                    2.06
                    if uiscale is ba.UIScale.SMALL
                    else 1.4
                    if uiscale is ba.UIScale.MEDIUM
                    else 1.0
                ),
                stack_offset=(0, -25)
                if uiscale is ba.UIScale.SMALL
                else (0, 0),
            )
        )

        self._back_button = ba.buttonwidget(
            parent=self._root_widget,
            position=(53, height - 60),
            size=(60, 60),
            scale=0.8,
            autoselect=True,
            label=ba.charstr(ba.SpecialChar.BACK),
            button_type='backSmall',
            on_activate_call=self._do_back
        )
        ba.containerwidget(
            edit=self._root_widget, cancel_button=self._back_button
        )

        self._title_text = ba.textwidget(
            parent=self._root_widget,
            position=(0, height - 52),
            size=(width, 25),
            text=ba.Lstr(resource='pluginSettingsText'),
            color=ba.app.ui.title_color,
            h_align='center',
            v_align='top'
        )

        self._y_position = 170 if uiscale is ba.UIScale.MEDIUM else 205
        self._plugins_button = ba.buttonwidget(
            parent=self._root_widget,
            position=(65,self._y_position),
            size=(350, 60),
            autoselect=True,
            label=ba.Lstr(resource='pluginsEnableAllText'),
            text_scale=1.0,
            on_activate_call=self._enable_all_plugins,
        )

        self._y_position -= 70
        self._plugins_button = ba.buttonwidget(
            parent=self._root_widget,
            position=(65,self._y_position),
            size=(350, 60),
            autoselect=True,
            label=ba.Lstr(resource='pluginsDisableAllText'),
            text_scale=1.0,
            on_activate_call=self._disable_all_plugins,
        )

        self._y_position -= 70
        self._enable_new_plugins_check_box = ConfigCheckBox(
            parent=self._root_widget,
            position=(65, self._y_position),
            size=(350, 60),
            configkey='Auto Enable New Plugins',
            displayname=ba.Lstr(resource='AutoEnableNewPluginsText'),
            scale=1.0,
            maxwidth=430
        )

    def _enable_all_plugins(self) -> None:
        cfg = ba.app.config
        plugs = cfg['Plugins']
        for plug in plugs:
            plugs[plug]['enabled'] = True
        cfg.apply_and_commit()

        ba.screenmessage(
            ba.Lstr(resource='settingsWindowAdvanced.mustRestartText'),
            color=(1.0, 0.5, 0.0),
        )

    def _disable_all_plugins(self) -> None:
        cfg = ba.app.config
        plugs = cfg['Plugins']
        for plug in plugs:
            plugs[plug]['enabled'] = False
        cfg.apply_and_commit()

        ba.screenmessage(
            ba.Lstr(resource='settingsWindowAdvanced.mustRestartText'),
            color=(1.0, 0.5, 0.0),
        )

    def _do_back(self) -> None:
        # pylint: disable=cyclic-import
        from bastd.ui.settings.plugins import PluginWindow

        ba.containerwidget(
            edit=self._root_widget, transition=self._transition_out
        )
        ba.app.ui.set_main_menu_window(
            PluginWindow(transition='in_left').get_root_widget()
        )
