import time
import threading
from flask import jsonify
# Assuming a basic rate limiting implementation.  For production, consider Redis or similar.
RATE_LIMIT = 5  # Maximum requests per minute
request_timestamps = []

def inject_fault(duration, endpoint, fault_type):
    """
    Injects a controlled fault into the system.

    Args:
        duration (int): The duration of the fault injection in seconds.
        endpoint (str): The API endpoint to inject the fault into.
        fault_type (str): The type of fault to inject ("latency", "error", "blackhole").

    Returns:
        tuple: A tuple containing a success message or an error message and status code.
    """

    if fault_type not in ["latency", "error", "blackhole"]:
        return jsonify({"message": "Invalid fault type"}), 400

    if not endpoint:
        return jsonify({"message": "Invalid endpoint"}), 400

    # Rate limiting check
    now = time.time()
    request_timestamps = [ts for ts in request_timestamps if ts > now - 60]  # Remove requests older than 1 minute
    if len(request_timestamps) >= RATE_LIMIT:
        return jsonify({"message": "Rate limit exceeded"}), 429

    request_timestamps.append(now)


    try:
        # Simulate fault injection (replace with actual chaos engineering platform integration)
        print(f"Injecting {fault_type} fault into {endpoint} for {duration} seconds.")

        if fault_type == "latency":
            # Simulate latency by sleeping.  In a real system, you'd modify the endpoint's behavior.
            time.sleep(duration)
            print(f"Latency fault injected into {endpoint} successfully.")

        elif fault_type == "error":
            # In a real system, this would involve triggering an error condition in the endpoint.
            print(f"Error fault injected into {endpoint} successfully.")
            pass  # Simulate success by passing 

        elif fault_type == "blackhole":
             #Simulate blackholing requests to the specified endpoint for a duration.
            time.sleep(duration)
            print(f"Blackhole fault injected into {endpoint} successfully")


    except Exception as e:
        print(f"Error injecting fault: {e}")
        return jsonify({"message": f"Fault injection failed: {str(e)}"}), 500

    return jsonify({"message": "Fault injected successfully."}), 200



def run_fault_injection(duration, endpoint, fault_type):
    """Runs the fault injection in a separate thread to handle concurrency."""
    threading.Thread(target=inject_fault, args=(duration, endpoint, fault_type)).start()


if __name__ == '__main__':
    # Example Usage (for testing)

    run_fault_injection(5, "/api/users", "latency")
    run_fault_injection(3, "/api/products", "error")
    run_fault_injection(2, "/api/orders", "blackhole")

    time.sleep(10) #Allow injections to complete before exiting for test purposes