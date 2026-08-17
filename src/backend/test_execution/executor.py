import uuid
import datetime
from flask import Flask, request, jsonify
# Assuming MOD-010 provides database interaction functionalities.  Adjust path if needed.
from src.backend.test_results.models import TestResult, TestExecution  # Import models
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker
import threading

app = Flask(__name__)

# Database configuration (replace with your actual database URL)
DATABASE_URL = "sqlite:///./test_results.db"  # Example SQLite database
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def check_user_permissions():
    """Placeholder for access control logic."""
    # Replace with your actual authentication/authorization mechanism.
    # For demonstration, assume all requests are allowed.
    return True

@app.route("/tests/execute", methods=["POST"])
def execute_tests():
    """Executes API tests and stores the results."""
    if not check_user_permissions():
        return jsonify({"error": "Unauthorized"}), 401

    request_data = request.get_json()
    test_case_ids = request_data.get("test_case_ids")

    if not test_case_ids:
        return jsonify({"error": "Test case IDs are required"}), 400

    execution_id = str(uuid.uuid4())
    threads = []

    for test_case_id in test_case_ids:
        thread = threading.Thread(target=run_test, args=(test_case_id, execution_id))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()  # Wait for all tests to complete
    

    return jsonify({"execution_id": execution_id}), 200


def run_test(test_case_id, execution_id):
    """Runs a single test case and stores the result."""
    try:
        # Simulate API call (replace with actual API interaction)
        api_response = simulate_api_call(test_case_id)  # Assume MOD-010 provides this function

        status = "pass" if api_response else "fail"

        with Session() as session:
            test_execution = TestExecution(test_case_id=test_case_id, start_time=datetime.datetime.now(), end_time=datetime.datetime.now())
            session.add(test_execution)
            session.commit()

            test_result = TestResult(execution_id=execution_id, status=status, response=api_response, test_case_id=test_case_id)
            session.add(test_result)
            session.commit()

    except Exception as e:
        print(f"Error executing test case {test_case_id}: {e}")
        # Handle API failures gracefully and report errors in the results.
        with Session() as session:
            test_execution = TestExecution(test_case_id=test_case_id, start_time=datetime.datetime.now(), end_time=datetime.datetime.now())
            session.add(test_execution)
            session.commit()

            test_result = TestResult(execution_id=execution_id, status="error", response=str(e), test_case_id=test_case_id)
            session.add(test_result)
            session.commit()


def simulate_api_call(test_case_id):
    """Simulates an API call based on the test case ID."""
    # Replace with actual API interaction using MOD-010 or other API client.
    # This is a placeholder for demonstration purposes.  Return True/False for success/failure
    if test_case_id == "test_case_1":
        return {"data": "Success!"}
    elif test_case_id == "test_case_2":
        return None  # Simulate failure
    else:
        return False #simulate not found

@app.route("/tests/results/<result_id>", methods=["GET"])
def get_test_result(result_id):
    """Retrieves a test result by ID."""
    with Session() as session:
        result = session.query(TestResult).filter_by(id=int(result_id)).first()

        if not result:
            return jsonify({"error": "Result not found"}), 404

        return jsonify({
            "status": result.status,
            "response": result.response,
            "test_case_id": result.test_case_id
        }), 200


if __name__ == "__main__":
    # Create tables if they don't exist (for development/testing)
    from sqlalchemy import MetaData

    metadata = MetaData()
    TestExecution.__table__.create(engine, checkexist=True)
    TestResult.__table__.create(engine, checkexist=True)
    app.run(debug=True)  # Remove debug=True for production