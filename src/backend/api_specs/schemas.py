from pydantic import BaseModel, validator
import base64
import io
import yaml
import json

class OpenAPISpecSchema(BaseModel):
    file: str

    @validator('file')
    def validate_file(cls, value):
        try:
            # Decode the base64 encoded string
            decoded_file = base64.b64decode(value)
            # Attempt to load as YAML first
            try:
                yaml.safe_load(io.BytesIO(decoded_file))
            except yaml.YAMLError:
                # If YAML fails, attempt to load as JSON
                try:
                    json.loads(decoded_file.decode('utf-8'))
                except json.JSONDecodeError:
                    raise ValueError("Invalid file format. Must be a valid YAML or JSON OpenAPI specification.")
            
            if len(decoded_file) > 10 * 1024 * 1024:  # Check for files larger than 10MB
                raise ValueError("File size exceeds the maximum allowed limit of 10MB.")

            return value
        except Exception as e:
            raise ValueError(f"Error processing file: {e}")