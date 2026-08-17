import subprocess
import time
import signal

def execute_script(script_content, timeout=10):
    """
    Executes a test script in a sandboxed environment with a timeout.

    Args:
        script_content (str): The content of the test script.
        timeout (int):  The maximum execution time for the script in seconds.

    Returns:
        tuple: A tuple containing the return code, stdout, and stderr of the script execution. 
               Returns (-1, None, error message) if an exception occurs during execution or timeout.
    """
    try:
        # Use subprocess to execute the script in a sandboxed manner.  This example uses python itself as the interpreter.
        process = subprocess.Popen(
            ['python', '-c', script_content],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid # Create a new session to isolate the process
        )

        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return_code = process.returncode

            if return_code is None and process.poll() is None:
                # Process still running after timeout - kill it.
                process.kill()
                return (-1, None, "Script execution timed out")


        except subprocess.TimeoutExpired:
            # Handle TimeoutException by killing the process group.
            group_id = os.getpgid(process.pid)
            os.killpg(group_id, signal.SIGTERM) 
            stdout, stderr = process.communicate() # Read any remaining output after kill.

            return (-1, None, "Script execution timed out")


        return (return_code, stdout.decode('utf-8'), stderr.decode('utf-8'))

    except Exception as e:
        return (-1, None, str(e))



import os  # Import os for setsid and other OS related operations.

if __name__ == '__main__':
    # Example Usage/Testing
    test_script = """
print("Test script started")
time.sleep(2) 
print("Test script finished successfully")
"""

    return_code, stdout, stderr = execute_script(test_script, timeout=5)

    print(f"Return Code: {return_code}")
    print(f"Stdout:\n{stdout}")
    print(f"Stderr:\n{stderr}")


    # Test case for a script that times out.
    timeout_script = """
while True:
    pass
"""

    return_code, stdout, stderr = execute_script(timeout_script, timeout=1)
    print(f"\nTimeout test:")
    print(f"Return Code: {return_code}")
    print(f"Stdout:\n{stdout}")
    print(f"Stderr:\n{stderr}")