import json
import random
from typing import Any, Dict, List, Optional

# Assuming MOD-001 handles secure storage - replace with actual implementation
try:
    from src.backend.data_storage.secure_storage import SecureStorage  # type: ignore
except ImportError:
    print("Warning: Could not import from 'src.backend.data_storage.secure_storage'.")
    SecureStorage = None


def load_test_scripts(script_path: str) -> List[Dict]:
    """Loads test scripts from a JSON file."""
    try:
        with open(script_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Test script file not found at {script_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in test script file: {script_path}")
        return []


def save_generated_data(data: Any, filename: str):
    """Saves generated data to a secure location."""
    if SecureStorage is None:
        print("Secure storage module not available. Data will not be saved securely.")
        return

    try:
        storage = SecureStorage()  # Initialize the SecureStorage object
        storage.save_data(data, filename) # Use the save_data function from secure_storage
    except Exception as e:
         print(f"Error saving data to secure storage: {e}")


def generate_random_value(data_type: str) -> Any:
    """Generates a random value based on the provided data type."""
    if data_type == "integer":
        return random.randint(1, 1000)
    elif data_type == "number":
        return round(random.uniform(1.0, 1000.0), 2)
    elif data_type == "string":
        return "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
    elif data_type == "boolean":
        return random.choice([True, False])
    else:
        return None  # Handle unknown types gracefully


def process_nested_data(schema: Dict, current_path: List[str] = []) -> Any:
    """Recursively processes nested data structures according to the schema."""
    if "type" in schema:
        if schema["type"] == "object":
            result = {}
            if "properties" in schema:
                for prop_name, prop_schema in schema["properties"].items():
                    new_path = current_path + [prop_name]
                    result[prop_name] = process_nested_data(prop_schema, new_path)
            return result
        elif schema["type"] == "array":
            if "items" in schema:
                item_schema = schema["items"]
                return [process_nested_data(item_schema, current_path)]  # Return a list with one element for now. Expand as needed
            else:
                return []
        else:
            return generate_random_value(schema["type"])
    elif "enum" in schema:
         return random.choice(schema["enum"])
    else:
        return None # Handle unknown cases



def conform_to_schema(data: Any, schema: Dict) -> Any:
    """Conforms the generated data to the API schema."""
    if isinstance(data, dict) and "properties" in schema:
        conformed_data = {}
        for key, prop_schema in schema["properties"].items():
            if key in data:
                conformed_data[key] = conform_to_schema(data[key], prop_schema)
            else:
                # If a required property is missing, handle it (e.g., generate a default value)
                if "required" in schema and key in schema["required"]:
                    conformed_data[key] = process_nested_data(prop_schema)  # Generate data according to the schema
                else:
                   conformed_data[key] = None # Handle missing optional properties.

        return conformed_data

    elif isinstance(data, list) and "items" in schema:
        item_schema = schema["items"]
        return [conform_to_schema(item, item_schema) for item in data]

    else:
        return data