from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Placeholder for database interaction.  In a real application this would connect to a database.
api_specs = [] # list of dictionaries: [{'id': '...', 'spec_url': '...'}]


def sanitize_url(url):
    """Sanitize the URL to prevent SSRF."""
    # Implement robust sanitization here.  This is just a basic example.
    # Consider using a library specifically designed for URL validation and sanitization.
    if not url.startswith("http://") and not url.startswith("https://"):
        return None  # Invalid protocol
    return url



@app.route('/api-specs', methods=['POST'])
def import_api_spec():
    """Imports an API specification from a URL."""
    data = request.get_json()
    if not data or 'spec_url' not in data:
        return jsonify({'error': 'Missing spec_url'}), 400

    spec_url = data['spec_url']

    sanitized_url = sanitize_url(spec_url)
    if sanitized_url is None:
        return jsonify({'error': 'Invalid URL provided'}), 400


    try:
        response = requests.get(sanitized_url, timeout=60) # Timeout to handle very large specs
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        spec = response.json()

        # Basic validation - check if it's a dictionary. More thorough validation needed in production.
        if not isinstance(spec, dict):
            return jsonify({'error': 'Invalid specification format'}), 400


        # Add to "database" and generate ID
        id = str(len(api_specs) + 1) # Simple id generation. Replace with UUID in a production app.
        api_specs.append({'id': id, 'spec_url': sanitized_url})

        return jsonify({'id': id}), 201

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Error fetching specification: {str(e)}'}), 400
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format in specification'}), 400
    except Exception as e:  #Catch all other errors, including circular references during parsing.
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True)