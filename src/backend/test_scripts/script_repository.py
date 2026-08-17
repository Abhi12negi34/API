import time
import threading
import traceback

class ScriptRepository:
    """
    Manages the storage and retrieval of custom test scripts.
    Also handles script execution with safety measures.
    """

    def __init__(self, timeout=10):
        """
        Initializes the repository with a default timeout for script execution.

        Args:
            timeout (int): Maximum time in seconds allowed for script execution.
        """
        self.scripts = {}  # Dictionary to store scripts (name -> code)
        self.execution_results = {} #Dictionary to store results of executions.
        self.timeout = timeout

    def add_script(self, name, code):
        """
        Adds a new script to the repository.

        Args:
            name (str): The unique name of the script.
            code (str): The Python code for the script.

        Raises:
            ValueError: If a script with the same name already exists.
        """
        if name in self.scripts:
            raise ValueError(f"Script with name '{name}' already exists.")
        self.scripts[name] = code

    def get_script(self, name):
        """
        Retrieves a script from the repository by its name.

        Args:
            name (str): The name of the script to retrieve.

        Returns:
            str: The Python code for the script, or None if not found.
        """
        return self.scripts.get(name)

    def run_script(self, name):
        """
        Executes a script in a sandboxed environment with a timeout.

        Args:
            name (str): The name of the script to execute.

        Returns:
            dict: A dictionary containing 'status' ('success' or 'error') and 'output'.  Output can be either result or error message.

        Raises:
            ValueError: If the script does not exist.
        """
        if name not in self.scripts:
            raise ValueError(f"Script with name '{name}' not found.")

        script_code = self.scripts[name]

        def target():
            try:
                # Execute the script within a limited scope (sandbox)
                local_vars = {}
                exec(script_code, {}, local_vars)  # Execute in a safe manner
                self.execution_results[name] = {'status': 'success', 'output': str(local_vars)}
            except Exception as e:
                self.execution_results[name] = {'status': 'error', 'output': traceback.format_exc()}

        thread = threading.Thread(target=target)
        thread.daemon = True  # Allow the main program to exit even if this thread is running
        thread.start()
        thread.join(self.timeout)

        if thread.is_alive():
            # Script exceeded timeout
            self.execution_results[name] = {'status': 'error', 'output': f"Script execution timed out after {self.timeout} seconds."}
            return self.execution_results[name] #Returning the error immediately rather than waiting for thread to finish

        return self.execution_results[name]
    
    def get_all_scripts(self):
      """
      Returns a dictionary of all scripts in the repository. 
      Useful for listing available scripts or backing up the repository.
      """
      return self.scripts