import requests
import json

def upload_api_spec(base_url, openapi_spec):
    """Uploads an OpenAPI specification to the server.

    Args:
        base_url (str): The base URL of the API.
        openapi_spec (str): The path to the OpenAPI specification file or the spec content itself.

    Returns:
        str: The ID of the uploaded API specification, or None if upload failed.
    """
    try:
        with open(openapi_spec, 'r') as f:
            spec_content = f.read()
        response = requests.post(f"{base_url}/api-specs", json={"openapi_spec": spec_content})
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json().get("id")
    except FileNotFoundError:
        print(f"Error: OpenAPI specification file not found at {openapi_spec}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error uploading API spec: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from server")
        return None


def generate_test_cases(base_url, api_spec_id):
    """Generates test cases for a given API specification ID.

    Args:
        base_url (str): The base URL of the API.
        api_spec_id (str): The ID of the API specification.

    Returns:
        list[str]: A list of test case IDs, or None if generation failed.
    """
    try:
        response = requests.post(f"{base_url}/test-cases/generate", json={"api_spec_id": api_spec_id})
        response.raise_for_status()
        return response.json().get("test_case_ids")
    except requests.exceptions.RequestException as e:
        print(f"Error generating test cases: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from server")
        return None


def execute_tests(base_url, test_case_ids):
    """Executes a list of test cases.

    Args:
        base_url (str): The base URL of the API.
        test_case_ids (list[str]): A list of test case IDs to execute.

    Returns:
        str: The ID of the test execution result, or None if execution failed.
    """
    try:
        response = requests.post(f"{base_url}/tests/execute", json={"test_case_ids": test_case_ids})
        response.raise_for_status()
        return response.json().get("result_id")
    except requests.exceptions.RequestException as e:
        print(f"Error executing tests: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from server")
        return None


if __name__ == '__main__':
    base_url = "http://localhost:8000"  # Replace with your API base URL

    # Example Usage
    openapi_spec_path = "example.yaml" # Path to an example OpenAPI specification file
    api_spec_id = upload_api_spec(base_url, openapi_spec_path)

    if api_spec_id:
        print(f"API Spec uploaded with ID: {api_spec_id}")
        test_case_ids = generate_test_cases(base_url, api_spec_id)

        if test_case_ids:
            print(f"Generated Test Case IDs: {test_case_ids}")
            result_id = execute_tests(base_url, test_case_ids)

            if result_id:
                print(f"Test Execution Result ID: {result_id}")
            else:
                print("Test execution failed.")
        else:
            print("Test case generation failed.")
    else:
        print("API spec upload failed.")