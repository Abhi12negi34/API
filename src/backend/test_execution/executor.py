from flask import Flask, request, jsonify
import uuid
import json
from src.backend.test_execution.models import TestExecution, TestResult  # Assuming models are in the same directory

app = Flask(__name__)

# Mock dependency injection - replace with actual imports/initialization
MOD_001 = None  # Placeholder for MOD-001 (e.g., Authentication module)
MOD_002 = None  # Placeholder for MOD-002 (e.g., Test Case Management module)

@app.route('/tests/execute', methods=['POST'])
def execute_test_cases():
    """
    Executes specified test cases and returns a result ID.
    """
    try:
        data = request.get_json()
        test_case_ids = data.get('test_case_ids')

        if not isinstance(test_case_ids, list):
            return jsonify({"error": "Invalid test case IDs format. Expected a list."}), 400
        
        # Validate test case IDs (replace with actual validation logic from MOD-002)
        for test_case_id in test_case_ids:
            if not isinstance(test_case_id, str):
                return jsonify({"error": "Invalid test case ID format."}), 400

        # Access control check (replace with actual role/permission check from MOD-001)
        if not has_permission(MOD_001, 'execute_tests'):
            return jsonify({"error": "Permission denied"}), 403
    
        result_id = str(uuid.uuid4())  # Generate a unique result ID
        test_execution = TestExecution(result_id=result_id, test_case_ids=test_case_ids)
        test_execution.save()

        # Execute tests (replace with actual execution logic using MOD-002 and store results)
        execute_and_store_results(test_case_ids, result_id)


        return jsonify({"result_id": result_id}), 200

    except Exception as e:
        print(f"Error executing tests: {e}") #Log the error
        return jsonify({"error": "Internal server error"}), 500


def execute_and_store_results(test_case_ids, result_id):
    """
    Executes test cases and stores results in the database.  This is a placeholder for integration with MOD-002.
    """

    for test_case_id in test_case_ids:
        try:
            # Replace this with actual test execution logic using MOD-002
            test_result = run_test(MOD_002, test_case_id)  # Mock call to external module

            if test_result: # Assuming test_result is a dictionary containing result data
                TestResult(result_id=result_id, test_case_id=test_case_id, result=json.dumps(test_result)).save()  # Store as JSON string for simplicity
        except Exception as e:
            print(f"Error executing test case {test_case_id}: {e}") # Log the error.

def run_test(mod_002, test_case_id):
    """
    Mocks running a test case using an external module (MOD-002).  Replace with actual integration logic.
    """
    # Replace with your integration with MOD-002 to execute the test case.

    if test_case_id == "test_1": #Mock data for demonstration
        return {"status": "passed", "message": "Test 1 passed!"}
    elif test_case_id == "test_2":
        return {"status": "failed", "message": "Test 2 failed due to invalid input."}
    else:
        return None # Test case not found or error during execution


@app.route('/tests/results/<result_id>', methods=['GET'])
def get_test_results(result_id):
    """
    Retrieves test results for a given result ID.
    """
    try:
        # Access control check (replace with actual role/permission check from MOD-001)
        if not has_permission(MOD_001, 'view_test_results'):
            return jsonify({"error": "Permission denied"}), 403

        test_execution = TestExecution.get(result_id)

        if test_execution is None:
            return jsonify({"error": "Result not found"}), 404
        
        # Retrieve test results from the database
        test_results = []
        for result in TestResult.query.filter_by(result_id=result_id):
             try:
                test_results.append(json.loads(result.result)) #Parse stored JSON string back to dictionary

             except json.JSONDecodeError:
                 print("Error decoding JSON from database") #log error if there is a parsing problem.
        
        return jsonify({"test_results": test_results}), 200

    except Exception as e:
        print(f"Error getting test results: {e}")  # Log the error
        return jsonify({"error": "Internal server error"}), 500


def has_permission(auth_module, permission):
    """
    Placeholder for access control check. Replace with actual implementation using MOD-001.
    """
    # In a real application, this would involve checking the user's role/permissions
    # against the required permission to perform the requested action.

    if auth_module: #Just ensure the module exists before returning true.
        return True
    else:
        return False