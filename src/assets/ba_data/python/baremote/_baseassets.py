# Released under the MIT License. See LICENSE for details.
#
"""The base assets the remote app hands to the engine."""

import babase

from babase import _remoteassets


def make_base_asset_set() -> babase.BaseAssetSet:
    """Build the art base draws the on-screen action buttons with.

    Almost every slot on :class:`babase.BaseAssetSet` is for things a
    controller never renders -- world reflections, explosion debris, the
    VR hands -- so the neutral builtin placeholders they start at are
    exactly right and are left alone.

    The exception is the engine's own touch controls, which *are* our
    main control surface (see ``base::TouchInput``). Its movement stick
    already draws from builtin art, but its four action buttons come
    from this set, and at the placeholder defaults they render as white
    cubes: ``meshes/box`` stretched under a flat ``textures/white``.

    Classic has art for them, but it lives in its asset package -- a
    large one a remote has no other reason to carry, for five assets.
    So they live in our own small package instead (see
    :mod:`babase._remoteassets`), which is also what makes the
    meta-scan bundle them into a plus-less build.

    Cheap to call: slots hold asset *handles*, so nothing loads here.
    """
    tex = _remoteassets.textures
    msh = _remoteassets.meshes
    assets = babase.BaseAssetSet()

    # One texture is bound for all four buttons; each mesh is a quad
    # uv-mapped to its own quadrant of the sheet. The quads are centered
    # rather than pre-positioned, so TouchInput lays the cluster out (see
    # set_action_button_meshes_prepositioned).
    assets.action_buttons = tex.action_buttons
    assets.action_button_bottom = msh.action_button_bottom
    assets.action_button_left = msh.action_button_left
    assets.action_button_right = msh.action_button_right
    assets.action_button_top = msh.action_button_top

    return assets
