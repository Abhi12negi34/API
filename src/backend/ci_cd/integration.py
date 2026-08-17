import logging
from flask import Flask, request, jsonify
import uuid
import threading
import time

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


def trigger_test_execution(pipeline_id, test_suite_id):
    """
    Triggers the test execution using MOD-011.

    Args:
        pipeline_id (str): The ID of the CI/CD pipeline.
        test_suite_id (str): The ID of the test suite to execute.

    Returns:
        str: The execution ID, or None if execution failed.
    """
    try:
        from src.backend.mod_011 import execute_tests  # Assuming MOD-011 is in this directory structure

        execution_id = str(uuid.uuid4())
        # Execute tests asynchronously to avoid blocking the API endpoint
        thread = threading.Thread(target=execute_tests, args=(pipeline_id, test_suite_id, execution_id))
        thread.start()
        return execution_id
    except ImportError as e:
        logging.error(f"Failed to import MOD-011: {e}")
        return None
    except Exception as e:
        logging.error(f"Test execution failed: {e}")
        return None


@app.route('/tests/trigger', methods=['POST'])
def trigger_tests():
    """
    API endpoint to trigger test execution from a CI/CD pipeline.
    """
    try:
        data = request.get_json()
        pipeline_id = data.get('pipeline_id')
        test_suite_id = data.get('test_suite_id')

        if not pipeline_id or not test_suite_id:
            logging.error("Invalid request parameters.")
            return jsonify({"error": "Invalid request parameters"}), 400

        execution_id = trigger_test_execution(pipeline_id, test_suite_id)

        if execution_id:
            return jsonify({"execution_id": execution_id}), 200
        else:
            logging.error("Failed to trigger test execution.")
            return jsonify({"error": "Internal server error"}), 500

    except Exception as e:
        logging.exception("An unexpected error occurred")  # Log the full traceback
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(debug=True)