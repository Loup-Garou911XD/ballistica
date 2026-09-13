# Released under the MIT License. See LICENSE for details.
#
# pylint: disable=missing-module-docstring, invalid-name

# This file is exec'ed by the spinoff system, allowing us to define
# values and behavior for this feature-set here in a programmatic way
# that can also be type-checked alongside other project Python code.

from batools.featureset import FeatureSet

# Grab the FeatureSet we're defining here.
fset = FeatureSet.get_active()

# We're just a library of Python stuff; no C++.
fset.has_python_binary_module = False

# Stuff we need.
fset.requirements = {'core', 'base', 'ui_v1', 'classic'}

# Same story as classic's wrapper: this one lives in bauiv1's package
# but is only ever read by our bauiv1lib.docuitest* modules.
fset.spinoff_extra_omit_paths = {
    'src/assets/ba_data/python/bauiv1/_docuiv2testassets.py',
}
