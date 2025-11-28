import sys
import os
from pathlib import Path

# Add the parent directory to sys.path so we can import simple_server
# This file is in review-system-core/functions/api.py
# simple_server.py is in review-system-core/
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from simple_server import app
import serverless_wsgi

def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
