"""
Pytest configuration: mock GUI dependencies before any module import so tests
run in headless environments (CI, servers without a display).
"""

import sys
from unittest.mock import MagicMock

# Must be set before matplotlib is imported anywhere
import matplotlib
matplotlib.use('Agg')

# Mock tkinter and the TkAgg backend — the tracker logic doesn't need them
for _mod in [
    'tkinter',
    'tkinter.scrolledtext',
    'tkinter.messagebox',
    'tkinter.ttk',
    'matplotlib.backends.backend_tkagg',
]:
    sys.modules[_mod] = MagicMock()
