from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/rest', methods=['POST'])
def rest_endpoint():
    """
    Handles REST API requests, validates input, and translates to a standardized format.
    """
    try:
        # Input Validation - Check for valid JSON
        if not request.is_json:
            return jsonify({"error": "Invalid JSON payload"}), 400

        data = request.get_json()

        # Further input validation based on expected schema (add more specific checks here)
        if not isinstance(data, dict):
            return jsonify({"error": "Payload must be a JSON object"}), 400


        # Payload size limit check - handle extremely large payloads to prevent DoS
        if len(str(data)) > 10 * 1024:  # Limit to 10KB (adjust as needed)
            return jsonify({"error": "Payload too large"}), 413

        # Translation to Standardized Format (example - adapt based on your internal format)
        standard_format = {
            "protocol": "REST",
            "data": data
        }

        # Process the standardized format (in a real app, call another module here)
        print(f"Received REST request: {standard_format}")  # Replace with actual processing

        return jsonify({"status": "success", "message": "Request processed successfully"}), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        print(f"An error occurred: {e}") # Log the error for debugging purposes
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(debug=True)