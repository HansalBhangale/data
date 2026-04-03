"""
GUI Package - Predictive Asset Allocation System

Modular Streamlit application with:
- Core business logic (mappings, portfolio building, backtesting)
- UI components (header, sidebar, charts, tables)
- Custom styling (theme)
"""

import sys
from pathlib import Path

# Add parent directory to path for importing composite module
sys.path.insert(0, str(Path(__file__).parent.parent))

__version__ = '1.0.0'
