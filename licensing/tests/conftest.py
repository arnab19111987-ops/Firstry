import importlib
import sys

# If anything under licensing/tests tries `import tests`, resolve it to this package
# (licensing.tests) rather than the global tests package. This keeps existing
# `from tests.xyz import ...` lines inside licensing tests working without a global clash.
if 'tests' not in sys.modules:
    sys.modules['tests'] = importlib.import_module('licensing.tests')
