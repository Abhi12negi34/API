import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class VersionedTests:
    """
    Manages test execution based on API versions.  This class assumes a database or data store
    exists where tests and their associated API versions are stored.  For simplicity, we'll 
    represent this with an in-memory list of dictionaries.
    """

    def __init__(self, test_data: List[Dict]):
        """
        Initializes the VersionedTests manager.

        Args:
            test_data: A list of dictionaries representing test cases. Each dictionary 
                       should have keys 'name', 'version', and 'test_function'.  
                       'test_function' should be a callable (e.g., a function).
        """
        self.tests = test_data

    def get_tests_for_version(self, api_version: str) -> List[Dict]:
        """
        Retrieves tests associated with a specific API version.

        Args:
            api_version: The API version string (e.g., "v1", "v2").

        Returns:
            A list of test dictionaries for the given API version.  Returns an empty 
            list if no tests are found for that version.
        """
        return [test for test in self.tests if test['version'] == api_version]


    def execute_tests(self, api_version: str):
        """
        Executes all tests associated with the specified API version.

        Args:
            api_version: The API version string to execute tests for.

        Raises:
            ValueError: If the API version does not exist (no tests are found).
        """
        tests = self.get_tests_for_version(api_version)

        if not tests:
            logger.error(f"No tests found for API version: {api_version}")
            raise ValueError(f"API version '{api_version}' does not exist.")


        successful_tests = []
        failed_tests = []

        for test in tests:
            try:
                test['test_function']()  # Execute the test function
                successful_tests.append(test['name'])
                logger.info(f"Test '{test['name']} ({api_version})' passed.")
            except Exception as e:
                failed_tests.append((test['name'], str(e)))
                logger.error(f"Test '{test['name']} ({api_version})' failed: {e}")

        if failed_tests:
            raise Exception(f"Tests Failed: {failed_tests}")
        else:
            print("All tests passed for version", api_version)


    def handle_deprecation(self, deprecated_version: str, new_version: str):
         """
         Handles API deprecation scenarios by executing tests against both the 
         deprecated and new versions.  This provides a safety net during transitions.

         Args:
             deprecated_version: The version being deprecated (e.g., "v1").
             new_version: The replacement version (e.g., "v2").
         """
         try:
            self.execute_tests(deprecated_version)
            print(f"Tests for deprecated API version '{deprecated_version}' passed.")

            self.execute_tests(new_version)
            print(f"Tests for new API version '{new_version}' passed.")
         except ValueError as e:
             logger.error(f"Error during deprecation handling: {e}")


if __name__ == '__main__':
    # Example Usage/Test Data
    def test_case_v1():
        print("Running test for v1")
        assert True

    def test_case_v2():
        print("Running test for v2")
        assert 1 == 1  # Another simple assertion.

    def test_case_v3():
        print("Running test for v3 - this might fail!")
        assert False #intentional failure



    test_data = [
        {'name': 'Test Case 1', 'version': 'v1', 'test_function': test_case_v1},
        {'name': 'Test Case 2', 'version': 'v2', 'test_function': test_case_v2},
        {'name': 'Test Case 3', 'version': 'v2', 'test_function': test_case_v2}, #multiple tests for a version
        {'name': 'Test Case 4', 'version': 'v3', 'test_function': test_case_v3}

    ]

    versioned_tests = VersionedTests(test_data)

    try:
        versioned_tests.execute_tests('v1')
        versioned_tests.execute_tests('v2')
    except ValueError as e:
        print(f"Error executing tests: {e}")

    #Demonstrate handling a non existent version
    try:
        versioned_tests.execute_tests('v4')
    except ValueError as e:
        print(f"Expected error when running v4: {e}")

    #Example of deprecation handling (this won't actually do anything useful 
    # without more complex setup, but shows how the function would be called)
    versioned_tests.handle_deprecation('v1', 'v2')