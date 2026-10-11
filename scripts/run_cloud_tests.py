"""Run tests with optional workspace-local test dependencies, without modifying global Python."""
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
deps = root / '.test-output' / 'deps'
if deps.exists():
    sys.path.insert(0, str(deps))
suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
