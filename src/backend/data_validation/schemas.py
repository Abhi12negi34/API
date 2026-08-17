from pydantic import BaseModel, ValidationError
from typing import Dict, Any, List

class DataSchema(BaseModel):
    """
    Base class for data schemas.  Subclasses should define the fields
    and their validation rules. Provides a consistent interface for
    validation and error handling.
    """

    def validate_data(self, data: Dict[str, Any]) -> None:
        """
        Validates the given data against the schema. Raises ValidationError if invalid.
        This method is called internally by the validator module.  External code should not call directly.
        """
        try:
            self.model_validate(data)
        except ValidationError as e:
            raise e

    @classmethod
    def get_errors_from_exception(cls, exc: ValidationError) -> List[str]:
        """
        Extracts user-friendly error messages from a Validation Error exception.
        This ensures that internal schema details are not exposed to the end user.
        """
        errors = []
        for error in exc.errors():
            errors.append(error["msg"])  # Return only the message, not other details
        return errors


class ExampleSchema(DataSchema):
    """
    Example schema for demonstration purposes. Replace with your actual schemas.
    This shows a simple example with string and integer fields.
    """
    name: str
    age: int
    email: str = None  # Optional field

    class Config:
        extra = 'forbid' # Prevents unexpected keys in the input data


class ComplexSchema(DataSchema):
    """
    Demonstrates a more complex schema with nested objects and lists.
    This is intended to test the handling of extremely complex structures.
    """
    id: int
    details: Dict[str, Any]
    tags: List[str]
    nested_object: 'NestedObject'  # Forward reference

    class Config:
        extra = 'forbid'


class NestedObject(BaseModel):
    value1: str
    value2: int = 0

    class Config:
       extra = 'forbid'



if __name__ == '__main__':
    # Example Usage (for testing)
    try:
        example_data = {"name": "John Doe", "age": 30, "email": "john.doe@example.com"}
        schema = ExampleSchema()
        schema.validate_data(example_data)
        print("Example data is valid.")

        invalid_data = {"name": 123, "age": "thirty", "extra_field": "something"} #trigger errors
        schema.validate_data(invalid_data)

    except ValidationError as e:
        print("Validation Error:", schema.get_errors_from_exception(e))


    try:
      complex_data = {
          "id": 1,
          "details": {"key1": "value1", "key2": 10},
          "tags":["tag1","tag2"],
          "nested_object": {"value1":"nested value", "value2":5}
      }

      complex_schema = ComplexSchema()
      complex_schema.validate_data(complex_data)
      print("Complex Data Valid")

      invalid_complex_data = {
            'id': 'one',  # Incorrect type
            'details': [1, 2, 3],  # incorrect type
            'tags': 123,   #incorrect type
            "nested_object": {"value1":"nested value"} #missing fields

      }
      complex_schema.validate_data(invalid_complex_data)

    except ValidationError as e:
        print("Complex Validation Error:", complex_schema.get_errors_from_exception(e))