import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import simple_server
# This file is in review-system-core/api/index.py
# simple_server.py is in review-system-core/
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from simple_server import app

# Vercel looks for a variable named 'app' in the entry point
# We already imported 'app' from simple_server
