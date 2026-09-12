# Released under the MIT License. See LICENSE for details.
#
# Auto-generated; do not edit by hand.
"""Asset-package wrapper for ``a-18011215.baremoteassets.260912`` (babase).

Art for the remote-control app's on-screen controls.

base::TouchInput draws a movement stick plus four action buttons; the stick
comes from builtin art but the buttons come from the app-mode's
babase.BaseAssetSet. Classic's copies of these live in BaClassicAssets, which a
remote has no other reason to carry -- so just these few live here.
"""

# ba_meta require api 9
# ba_meta require asset-package a-18011215.baremoteassets.260912

# pylint: disable=useless-suppression
# pylint: disable=too-many-lines
# pylint: disable=too-few-public-methods, disallowed-name

from typing import TYPE_CHECKING

from babase._assetref import AssetGroup

_ASSET_PACKAGE = 'a-18011215.baremoteassets.260912'

if TYPE_CHECKING:
    from babase._assetref import MeshHandle, TextureHandle

    class MeshesGroup:
        """
        ::

            One quad per action button, each uv-mapped to its own quadrant of
            the glyph sheet. Centered on the origin; TouchInput positions the
            cluster.

            See source for the full asset list.
        """

        action_button_bottom: MeshHandle
        action_button_left: MeshHandle
        action_button_right: MeshHandle
        action_button_top: MeshHandle

    class TexturesGroup:
        """
        ::

            Glyph sheet for the action buttons, 2x2. Flat white shapes -- the
            engine tints each button as it draws.

            See source for the full asset list.
        """

        action_buttons: TextureHandle

    #: The ``meshes`` group - 4 assets (``action_button_bottom``,
    #: ``action_button_left``, ``action_button_right``, ``action_button_top``).
    #: Full list in source.
    meshes: MeshesGroup

    #: The ``textures`` group - 1 asset (``action_buttons``). Full list in
    #: source.
    textures: TexturesGroup

_TREE = {
    'meshes': {
        'action_button_bottom': 'm',
        'action_button_left': 'm',
        'action_button_right': 'm',
        'action_button_top': 'm',
    },
    'textures': {'action_buttons': 't'},
}


if not TYPE_CHECKING:
    meshes = AssetGroup(_ASSET_PACKAGE, _TREE['meshes'], 'meshes')
    textures = AssetGroup(_ASSET_PACKAGE, _TREE['textures'], 'textures')
