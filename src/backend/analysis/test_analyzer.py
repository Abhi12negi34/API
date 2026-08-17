from flask import Flask, jsonify, request
import datetime
# Assuming MOD-007 is the RCA engine module
from src.backend.analysis import rca_engine  

app = Flask(__name__)

test_results = {} # In-memory storage for test results - {result_id: {timestamp, errors, failures}}

@app.route("/tests/results/<string:result_id>", methods=["GET"])
def get_test_result(result_id):
    """
    Retrieves test result details by ID.
    """
    if result_id not in test_results:
        return jsonify({"error": "Test result not found"}), 404

    result = test_results[result_id]
    errors = result.get("errors", 0)
    failures = result.get("failures", 0)

    # Generate a basic RCA report (can be enhanced with MOD-007 integration)
    rca_report = generate_basic_rca(errors, failures)

    return jsonify({"errors": errors, "failures": failures, "rca_report": rca_report}), 200


@app.route("/rca/analyze", methods=["POST"])
def analyze_test_result():
    """
    Analyzes a test result and returns an RCA report.  Expects the test_result_id in the request body.
    """
    data = request.get_json()
    test_result_id = data.get("test_result_id")

    if not test_result_id:
        return jsonify({"error": "Test result ID is required"}), 400

    if test_result_id not in test_results:
        return jsonify({"error": "Test result not found"}), 404
    
    # Use the RCA engine module (MOD-007) to generate a detailed report
    rca_report = rca_engine.generate_rca_report(test_result_id, test_results)

    return jsonify({"rca_report": rca_report}), 200


def record_test_result(result_id, errors, failures):
    """Records the test result with a timestamp."""
    timestamp = datetime.datetime.now()
    test_results[result_id] = {
        "timestamp": timestamp,
        "errors": errors,
        "failures": failures
    }

def generate_basic_rca(errors, failures):
    """Generates a basic RCA report based on error and failure counts."""
    total_assertions = errors + failures  # Simple assumption for demonstration
    if total_assertions == 0:
        return "All tests passed."

    failure_rate = (failures / total_assertions) * 100 if total_assertions > 0 else 0

    report = f"Test Summary:\nTotal Assertions: {total_assertions}\nErrors: {errors}\nFailures: {failures}\nFailure Rate: {failure_rate:.2f}%"
    return report


if __name__ == "__main__":
    # Example usage and test data (for local testing)
    record_test_result("test1", 0, 0)
    record_test_result("test2", 2, 5)
    record_test_result("test3", 1, 10)

    app.run(debug=True) #Don't use debug mode in production.