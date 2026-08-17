from src.backend.test_data_creation import utils
import json
import random

def generate_test_data(schema, num_records=1):
    """
    Generates realistic test data based on an API schema (OpenAPI/Swagger).

    Args:
        schema (dict): The OpenAPI schema dictionary.
        num_records (int): The number of records to generate.  Defaults to 1.

    Returns:
        list: A list of generated test data records (dictionaries).  Returns an empty list if the schema is invalid or generation fails.
    """

    if not isinstance(schema, dict) or 'properties' not in schema:
        print("Error: Invalid schema format.")
        return []

    data = []
    for _ in range(num_records):
        record = {}
        for property_name, property_details in schema['properties'].items():
            try:
                record[property_name] = generate_value(property_details)
            except Exception as e:
                print(f"Error generating value for property {property_name}: {e}")
                # Optionally handle the error - skip this record or return an error.  For now, continue to next property.
                record[property_name] = None # Or a default value.

        data.append(record)

    return data



def generate_value(property_details):
    """
    Generates a single value based on the property details in the schema.

    Args:
        property_details (dict): A dictionary containing property type and other details.

    Returns:
        Any: The generated value for the property.
    """

    property_type = property_details.get('type')

    if property_type == 'string':
        return utils.generate_random_string(length=10)  # Use utility function. Consider min/max length from schema.
    elif property_type == 'integer':
        return random.randint(0, 1000) # consider min/max and format (e.g., int32, int64).  Use utils if needed for more complex ranges.
    elif property_type == 'number':
        return round(random.uniform(0.0, 100.0), 2)
    elif property_type == 'boolean':
        return random.choice([True, False])
    elif property_type == 'array':
        items = property_details.get('items', {}) # Handle cases where items is missing.
        if items:
            # Assuming homogeneous array for simplicity.  Could be extended to handle schemas.
            array_length = random.randint(1, 5)
            return [generate_value(items) for _ in range(array_length)]
        else:
            return [] # Empty Array if no item specification exists
    elif property_type == 'object':
        # Simple object - recursively generate properties based on sub-schema.  This is where handling complex/nested types becomes crucial.

        properties = property_details.get('properties', {})
        if not properties:
            return {} # Return empty dict for object with no defined props.

        obj = {}
        for prop_name, prop_detail in properties.items():
           try:
                obj[prop_name] = generate_value(prop_detail)
           except Exception as e:
               print(f"Error generating value within Object for property {prop_name}: {e}")
               obj[prop_name] = None

        return obj


    else:
        # Handle unknown types or add more specific logic.  Return None or a default value.
        print(f"Warning: Unsupported type: {property_type}. Returning None.")
        return None # Or a sensible default based on application needs



if __name__ == '__main__':
    # Example usage with a sample schema (replace with your actual schema)
    sample_schema = {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'age': {'type': 'integer'},
            'is_active': {'type': 'boolean'},
            'scores': {'type': 'array', 'items': {'type': 'number'}},
            'address': {
                'type': 'object',
                'properties': {
                    'street': {'type': 'string'},
                    'city': {'type': 'string'}
                }
            }
        }
    }

    test_data = generate_test_data(sample_schema, num_records=3)
    print(json.dumps(test_data, indent=2))