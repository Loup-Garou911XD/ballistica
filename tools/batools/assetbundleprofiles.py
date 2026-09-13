# Released under the MIT License. See LICENSE for details.
#
"""Declarative definitions of asset-package *bundle profiles*.

A *bundle profile* names the set of asset packages baked into a
particular build, each with its texture profile / quality / language.
:func:`batools.pcommands2.asset_bundle_build` assembles a profile into
``.cache/asset_bundle/<profile>/`` and the ``stage_build`` pcommand
copies that into the build's ``ba_data/``. The two agree purely on the
profile *name* (the cache dir is namespaced by it), so they can't drift.

Today's profiles are 'minimal' -- just the builtin construct package
(``gui-minimal`` with real fallback-flavor textures, ``headless-minimal``
with null textures). New profiles -- e.g. a desktop build that also
bundles a platform-flavored ``baclassicassets`` -- are added here as plain
data. The assemble + stage + runtime machinery is already package-plural
(the bundle manifest is keyed by apverid and every consumer iterates it),
so carrying additional packages needs no code changes -- only a new
entry below (and, for a new package, its projectconfig pin).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BundlePackage:
    """One asset package within a bundle profile."""

    #: projectconfig field holding this package's pinned apverid (e.g.
    #: ``'assets'`` for the builtin construct package). Resolved to a
    #: concrete apverid at assemble time. None when :attr:`apverid`
    #: names the package directly.
    projectconfig_key: str | None

    #: Texture flavor to assemble. ``'null'`` ships a single shared
    #: empty blob per logical texture (headless builds); real flavors
    #: ship image data (``'fallback_v1'`` today; ``'desktop_v1'`` /
    #: ``'astc'`` / ... as per-platform flavors come online).
    texture_profile: str

    #: Texture quality tier (e.g. ``'regular'``, ``'high'``).
    texture_tier: str

    #: Language bucket to include (e.g. ``'eng'``).
    language: str

    #: Explicit apverid, for packages discovered from the source tree
    #: rather than pinned in projectconfig (see
    #: :func:`packages_for_project`). Exactly one of this and
    #: :attr:`projectconfig_key` is set; profiles declared below always
    #: use the key, so only discovered packages carry this.
    apverid: str | None = None

    def resolve_apverid(self, pconfig: dict) -> str:
        """Our concrete apverid, following the projectconfig pin if any.

        The one place the two identity fields above are collapsed, so no
        caller has to branch on which of them is set.
        """
        from efro.error import CleanError

        if self.apverid is not None:
            return self.apverid

        assert self.projectconfig_key is not None
        value = pconfig.get(self.projectconfig_key)
        if not isinstance(value, str) or not value:
            raise CleanError(
                f"Need a string '{self.projectconfig_key}' value in"
                f' projectconfig; got'
                f' {type(value).__name__} value {value!r}.'
            )
        return value


@dataclass(frozen=True)
class BundleProfile:
    """A named set of asset packages to bundle into a build."""

    name: str
    packages: tuple[BundlePackage, ...]

    #: Whether a plus-less project should additionally bundle every
    #: package its source tree asks for (see
    #: :func:`packages_for_project`). True for profiles feeding a build
    #: that draws; a headless build has no ui to feed, and one without
    #: plus is a server.
    bundles_discovered_packages: bool = False


# The builtin/construct package, pinned via projectconfig's "assets"
# field. The minimal profiles carry only this -- the gui one with real
# (fallback-flavor) textures, the headless one with null textures (same
# wrapper-module layout, no image data).
_BUILTINS_GUI = BundlePackage(
    projectconfig_key='assets',
    texture_profile='fallback_v1',
    texture_tier='regular',
    language='eng',
)
_BUILTINS_HEADLESS = BundlePackage(
    projectconfig_key='assets',
    texture_profile='null',
    texture_tier='regular',
    language='eng',
)

PROFILES: dict[str, BundleProfile] = {
    'gui-minimal': BundleProfile(
        name='gui-minimal',
        packages=(_BUILTINS_GUI,),
        bundles_discovered_packages=True,
    ),
    'headless-minimal': BundleProfile(
        name='headless-minimal', packages=(_BUILTINS_HEADLESS,)
    ),
}


def get_profile(name: str) -> BundleProfile:
    """Look up a bundle profile by name (or raise ``CleanError``)."""
    from efro.error import CleanError

    profile = PROFILES.get(name)
    if profile is None:
        valid = ', '.join(sorted(PROFILES))
        raise CleanError(
            f"Unknown asset-bundle profile '{name}'."
            f' Valid profiles: {valid}.'
        )
    return profile


def packages_for_project(
    profile: BundleProfile, projroot: str
) -> tuple[BundlePackage, ...]:
    """Return the packages to bundle for a profile in a given project.

    Normally this is just what the profile declares. The exception is a
    project built without the ``plus`` feature-set: plus is what
    resolves asset-packages from the connected node at runtime, so
    without it construct-mode can only ever satisfy packages that are
    already local. Anything the source tree asks for and the build does
    not carry would fail the boot outright.

    So for such a project we bundle exactly what the meta-scan finds --
    the same set construct-mode will demand -- rather than a hardcoded
    list. That keeps a plus-less build self-contained and offline by
    construction, and stays correct for any feature-set combination
    without anyone maintaining a parallel package list.

    Profiles opt into this with
    :attr:`BundleProfile.bundles_discovered_packages`; a headless one
    does not, since it draws nothing and a headless build with no plus
    is a server rather than something with a ui to feed.
    """
    from pathlib import Path

    from efrotools.project import getprojectconfig

    from batools.featureset import FeatureSet

    # Only profiles that feed a drawing build want this, and only a
    # plus-less project needs it.
    if not profile.bundles_discovered_packages:
        return profile.packages

    fsets = {f.name for f in FeatureSet.get_all_for_project(projroot)}
    if 'plus' in fsets:
        return profile.packages

    # Reuse the discovery that already knows how to find every
    # ``# ba_meta require asset-package`` line in the tree.
    from batools.assetpins import discover_wrapper_apverids

    template = profile.packages[0]
    wanted = discover_wrapper_apverids(Path(projroot))

    # Whatever the profile already declares stays as-is, so the builtin
    # construct package keeps coming from its projectconfig pin; we only
    # add what the tree asks for on top, at the same flavor. Resolve the
    # declared pins once here rather than per discovered package.
    pconfig = getprojectconfig(Path(projroot))
    declared_names = {
        _package_name(pkg.resolve_apverid(pconfig)) for pkg in profile.packages
    }

    out = list(profile.packages)
    for apverid in sorted(wanted):
        name = _package_name(apverid)
        if name in declared_names:
            continue
        out.append(
            BundlePackage(
                projectconfig_key=None,
                texture_profile=template.texture_profile,
                texture_tier=template.texture_tier,
                language=template.language,
                apverid=apverid,
            )
        )
    return tuple(out)


def _package_name(apverid: str) -> str:
    """``a-0.bauiv1assets.260831a`` -> ``bauiv1assets``."""
    from batools.assetpins import account_and_package_or_bare_dev

    _account, package = account_and_package_or_bare_dev(apverid)
    return package
