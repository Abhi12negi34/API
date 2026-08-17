import unittest
import requests
import json

class ApiTests(unittest.TestCase):

    BASE_URL = "http://localhost:8000"  # Replace with your backend URL

    def test_execute_valid_ids(self):
        test_case_ids = ["test1", "test2"]
        response = requests.post(f"{self.BASE_URL}/tests/execute", json={"test_case_ids": test_case_ids})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result_id", data)

    def test_execute_invalid_ids(self):
        test_case_ids = ["invalid_id"]
        response = requests.post(f"{self.BASE_URL}/tests/execute", json={"test_case_ids": test_case_ids})
        self.assertEqual(response.status_code, 400)

    def test_get_results_valid_id(self):
        # First execute a test to get a result ID
        test_case_ids = ["test1"]
        execute_response = requests.post(f"{self.BASE_URL}/tests/execute", json={"test_case_ids": test_case_ids})
        self.assertEqual(execute_response.status_code, 200)
        data = execute_response.json()
        result_id = data["result_id"]

        # Then get the results for that ID
        get_results_response = requests.get(f"{self.BASE_URL}/tests/results/{result_id}")
        self.assertEqual(get_results_response.status_code, 200)
        data = get_results_response.json()
        self.assertIn("test_results", data)

    def test_get_results_invalid_id(self):
        get_results_response = requests.get(f"{self.BASE_URL}/tests/results/nonexistent_id")
        self.assertEqual(get_results_response.status_code, 404)

    def test_execute_empty_ids(self):
        response = requests.post(f"{self.BASE_URL}/tests/execute", json={"test_case_ids": []})
        self.assertEqual(response.status_code, 200) # Or potentially 400 depending on desired behavior

    def test_get_results_unexpected_format(self):
         # First execute a test to get a result ID
        test_case_ids = ["test1"]
        execute_response = requests.post(f"{self.BASE_URL}/tests/execute", json={"test_case_ids": test_case_ids})
        self.assertEqual(execute_response.status_code, 200)
        data = execute_response.json()
        result_id = data["result_id"]

        # Then get the results for that ID and check for unexpected format (e.g., string instead of list)
        get_results_response = requests.get(f"{self.BASE_URL}/tests/results/{result_id}")
        self.assertEqual(get_results_response.status_code, 200)
        data = get_results_response.json()
        self.assertIsInstance(data.get("test_results"), list)

if __name__ == '__main__':
    unittest.main()