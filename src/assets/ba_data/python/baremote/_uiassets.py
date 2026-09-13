# Released under the MIT License. See LICENSE for details.
#
"""The ui assets the remote app hands to ui_v1."""

import bauiv1 as bui
from bauiv1 import _uiv1assets


def make_ui_asset_set() -> bui.UIAssetSet:
    """Build the set of art the remote wants the ui layer drawn with.

    UIAssetSet's constructor arguments are the slots ui_v1 has no art
    of its own for -- classic's toolbar, store and currency furniture.
    A remote control has none of that on screen, so rather than pull in
    classic's art package for images we never draw, every one of them
    gets a neutral placeholder from ui_v1's own package. Everything
    else on the set already starts at ui_v1's art and is left alone.

    Cheap to call: slots hold asset *handles*, so nothing loads here.
    Loading happens when the set is applied at activation, and only
    for the slots that survive config amendment -- which means these
    placeholders cost nothing unless something actually draws them.
    """
    tex = _uiv1assets.textures.white
    msh = _uiv1assets.meshes.image1x1
    return bui.UIAssetSet(
        level_icon=tex,
        trophy=tex,
        chest_icon_empty=tex,
        log_icon=tex,
        leaderboards_icon=tex,
        inventory_icon=tex,
        store_icon=tex,
        store_character_xmas=tex,
        coin=tex,
        tickets=tex,
        lock=tex,
        tv=tex,
        achievements_icon=tex,
        settings_icon=tex,
        currency_meter=msh,
        currency_plus_button=msh,
        toolbar_backing_top2=msh,
        toolbar_backing_bottom2=msh,
    )
