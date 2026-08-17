import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/resilience/test', methods=['POST'])
def resilience_test():
    """
    Tests API stability under stress and reports latency & error rates.
    """
    data = request.get_json()
    duration = data.get('duration')
    endpoint = data.get('endpoint')

    if not duration or not endpoint:
        return jsonify({'error': 'Invalid endpoint or duration'}), 400

    try:
        duration = int(duration)
    except ValueError:
        return jsonify({'error': 'Duration must be an integer'}), 400

    start_time = time.time()
    results = []
    errors = 0

    for _ in range(100):  # Simulate stress with 100 requests
        try:
            response = requests.get(endpoint)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            latency = response.elapsed.total_seconds()
            results.append(latency)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            errors += 1

    end_time = time.time()
    total_time = end_time - start_time
    average_latency = sum(results) / len(results) if results else 0
    error_rate = errors / 100

    return jsonify({'results': results, 'average_latency': average_latency, 'error_rate': error_rate}), 200



@app.route('/fault-injection/inject', methods=['POST'])
def inject_fault():
    """
    Injects faults into a specified endpoint.  Currently a stub - actual implementation would vary greatly.
    Isolates fault injection to prevent cascading failures.  This basic version just logs the request.
    A production system needs robust error handling and potentially rollback mechanisms.
    """
    data = request.get_json()
    fault_type = data.get('type')
    endpoint = data.get('endpoint')

    if not fault_type or not endpoint:
        return jsonify({'error': 'Invalid endpoint or fault type'}), 400

    # In a real system, this would involve modifying the target service's behavior.
    # This could be done via mocking, circuit breaking, or other techniques.
    try:
      # Simulate potential external dependency issues (e.g., network timeout)
      if fault_type == "timeout": 
        time.sleep(5) #simulate a delay.  In a real application this would trigger the timeout condition

      print(f"Fault injection requested for endpoint '{endpoint}' with type '{fault_type}'.")
      # Add more sophisticated fault injection logic here as needed.

    except Exception as e:
        print(f"Error during fault injection: {e}") # log error, isolate failure


    return jsonify({}), 200  # Indicate success (even if the fault didn't perfectly manifest)

if __name__ == '__main__':
    app.run(debug=True)