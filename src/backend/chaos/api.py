from flask import Flask, request, jsonify
import threading
import time
from functools import lru_cache

app = Flask(__name__)

# Rate limiting settings (requests per minute)
RATE_LIMIT = 10
rate_limit_lock = threading.Lock()
request_timestamps = []

def is_rate_limited():
    with rate_limit_lock:
        now = time.time()
        # Remove timestamps older than one minute
        global request_timestamps
        request_timestamps = [ts for ts in request_timestamps if now - ts < 60]
        if len(request_timestamps) >= RATE_LIMIT:
            return True
        request_timestamps.append(now)
        return False

@lru_cache(maxsize=128)
def get_fault_injector():
    """Placeholder for potential fault injector initialization."""
    # In a real implementation, this might initialize a connection to
    # the chaos engineering platform.  For now, it just returns None.
    return None

@app.route('/fault-injection/inject', methods=['POST'])
def inject_fault():
    if is_rate_limited():
        return jsonify({"error": "Rate limit exceeded."}), 429

    data = request.get_json()
    duration = data.get('duration')
    endpoint = data.get('endpoint')
    fault_type = data.get('fault_type')

    if not all([duration, endpoint, fault_type]):
        return jsonify({"error": "Missing parameters."}), 400

    if fault_type not in ["latency", "error", "blackhole"]:
        return jsonify({"error": "Invalid fault type."}), 400

    # Basic input validation (add more as needed)
    if not isinstance(duration, int) or duration <= 0:
        return jsonify({"error": "Duration must be a positive integer."}), 400
    if not isinstance(endpoint, str) or not endpoint:
        return jsonify({"error": "Endpoint must be a non-empty string."}), 400

    try:
        # In a real implementation, this would interact with the chaos engineering platform.
        # For now, we just log the request and simulate success.
        print(f"Injecting {fault_type} fault on endpoint '{endpoint}' for {duration} seconds.")

        # Simulate fault injection (replace with actual integration)
        def inject():
            time.sleep(duration)  #Simulate duration
            print("Fault injected successfully (simulated).")

        thread = threading.Thread(target=inject)
        thread.start() #Start a new thread for each request to handle concurrent injections

        return jsonify({"message": "Fault injected successfully."}), 200

    except Exception as e:
        print(f"Error injecting fault: {e}")
        return jsonify({"error": f"Failed to inject fault: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)