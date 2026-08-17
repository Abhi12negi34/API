from flask import Flask, request, jsonify
import json
import os
# Assuming MOD-014 provides a function to generate test cases from a spec.
# Replace 'mod014' with the actual module name if different.
try:
    from src.backend.module_014 import generate_test_cases  # Import here to avoid circular dependency issues during initial setup.
except ImportError:
    print("Warning: Module MOD-014 (src/backend/module_014) not found.")
    generate_test_cases = None

app = Flask(__name__)

@app.route('/test-cases/generate', methods=['POST'])
def generate_test_cases_endpoint():
    """
    Generates test cases from an API specification.
    """
    try:
        data = request.get_json()
        spec_id = data.get('spec_id')

        # Sanitize user input to prevent injection vulnerabilities
        if not spec_id:
            return jsonify({'error': 'Spec ID is required'}), 400
        
        sanitized_spec_id = ''.join(c for c in spec_id if c.isalnum() or c == '_' or c == '-')  # Basic sanitization

        # Check if specification exists (placeholder - replace with actual DB check)
        if sanitized_spec_id not in get_available_spec_ids(): #Placeholder function to simulate db interaction
            return jsonify({'error': 'Specification not found'}), 404

        if generate_test_cases is None:
            return jsonify({'error':'Module MOD-014 not initialized. Test case generation unavailable.'}), 500
        
        # Generate test cases using the imported function from MOD-014
        try:
            test_case_ids = generate_test_cases(sanitized_spec_id) # Assuming this returns a list of IDs
        except Exception as e:
            print(f"Error during test case generation: {e}")  # Log the error for debugging.
            return jsonify({'error': 'Failed to generate test cases'}), 500

        return jsonify({'test_case_ids': test_case_ids}), 200

    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")  # Log unexpected errors for debugging
        return jsonify({'error': 'Internal server error'}), 500

def get_available_spec_ids():
    """
    Placeholder function to simulate a database lookup. Replace with actual DB interaction.
    """
    # In real implementation, fetch from database or config file.
    return ["spec1", "spec2", "test_spec"]  # Example values


if __name__ == '__main__':
    app.run(debug=True)