# Released under the MIT License. See LICENSE for details.
#
# pylint: disable=missing-module-docstring, invalid-name

# This file is exec'ed by the spinoff system, allowing us to define
# values and behavior for this feature-set here in a programmatic way
# that can also be type-checked alongside other project Python code.

from batools.featureset import FeatureSet

# Grab the FeatureSet we're defining here.
fset = FeatureSet.get_active()

# Stuff we need. ui_v1 is needed outright (not softly) because our
# app-mode is what registers uiv1 as the engine's ui-delegate; without
# that nobody does it in a classic-less build and no widget ever draws.
#
# Deliberately no plus: a remote should work on a LAN with no account
# and no internet. Plus is normally what fetches asset-packages at
# runtime, so a build without it bundles everything the meta-scan asks
# for instead (see batools.assetbundleprofiles.packages_for_project).
fset.requirements = {'core', 'base', 'ui_v1'}

# Creates a RemoteAppSubsystem at 'ba*.app.remote'.
fset.has_python_app_subsystem = True
