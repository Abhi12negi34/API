from flask import jsonify
import jsonschema
from jsonschema import ValidationError
# Assuming MOD-018 provides a logging utility.  Adjust path if needed
from src.backend.data_validation.schemas import data_schemas

class Validator:
    """
    Validates incoming data against predefined schemas.
    """

    def __init__(self):
        pass

    @staticmethod
    def validate_data(data, schema_name):
        """
        Validates the given data against the specified schema.

        Args:
            data (dict): The data to validate.
            schema_name (str): The name of the schema to use for validation.

        Returns:
            tuple: A tuple containing a boolean indicating validity and a list of error messages.  If valid, returns (True, []). If invalid, returns (False, [list of errors]).
        """
        if schema_name not in data_schemas:
            return False, ["Schema not found."]

        schema = data_schemas[schema_name]

        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, []
        except ValidationError as e:
            errors = Validator._extract_error_messages(e)
            return False, errors
        except jsonschema.SchemaError as e:  # Handle invalid schemas themselves
             # Log the schema error (important for debugging schema issues)
            print(f"Schema Error for {schema_name}: {e}") # replace print with logging call from MOD-018 if available
            return False, ["Invalid schema definition."] 

    @staticmethod
    def _extract_error_messages(validation_error):
        """
        Extracts user-friendly error messages from a jsonschema ValidationError.  Handles nested errors.

        Args:
            validation_error (ValidationError): The validation error object.

        Returns:
            list: A list of human-readable error messages.
        """
        errors = []
        if isinstance(validation_error, ValidationError):
            errors.append(f"Validation Error: {validation_error.message}")
            if 'cause' in validation_error and validation_error.cause is not None:
                 # Recursively extract errors from the cause (handles nested validations)
                nested_errors = Validator._extract_error_messages(validation_error.cause)
                errors.extend(nested_errors)

        return errors


def create_validator():
    """
    Factory function to create a Validator instance.
    """
    return Validator()

if __name__ == '__main__':
    # Example Usage (for testing purposes only - remove in production)
    from src.backend.data_validation.schemas import example_data, example_schema
    validator = create_validator()
    is_valid, errors = validator.validate_data(example_data, "example")

    if is_valid:
        print("Data is valid.")
    else:
        print("Data is invalid:")
        for error in errors:
            print(f"- {error}")