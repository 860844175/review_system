import sys
import os
from pathlib import Path

# Add the parent directory to sys.path so we can import simple_server
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

try:
    from simple_server import app
    from apig_wsgi import make_lambda_handler

    # Configure apig_wsgi to handle binary types if needed, but for now keep it simple
    handler = make_lambda_handler(app, binary_support=True)

except Exception as e:
    # Fallback handler to print error to logs and return 500
    print(f"CRITICAL ERROR: Failed to import app or dependencies: {e}")
    import traceback
    traceback.print_exc()
    
    def handler(event, context):
        return {
            "statusCode": 500,
            "body": f"Internal Server Error: {str(e)}"
        }
