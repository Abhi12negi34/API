from fastapi import FastAPI, File, UploadFile, HTTPException
import base64
import json

app = FastAPI()

# In-memory storage for simplicity.  In a production system, this would be a database.
api_specs = {}
next_id = 1


@app.post("/api-specs")
async def import_api_spec(file: str):
    """
    Imports an OpenAPI specification from a base64 encoded string.

    Args:
        file (str): Base64 encoded OpenAPI specification file.

    Returns:
        dict: The ID of the imported API specification.

    Raises:
        HTTPException: 400 if the file format is invalid, 500 for internal server errors.
    """
    try:
        # Sanitize input:  Limit file size to prevent DoS attacks and excessive memory usage
        if len(file) > 10 * 1024 * 1024: # 10MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum allowed size is 10MB.")

        # Decode the base64 encoded string
        spec_content = base64.b64decode(file).decode('utf-8')

        # Validate that the content is valid JSON
        try:
            json.loads(spec_content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format.")
        

        # Store the specification (in a real app, this would be in a database)
        global next_id
        api_specs[next_id] = spec_content
        spec_id = str(next_id)
        next_id += 1


        return {"id": spec_id}

    except Exception as e:
        # Log the error for debugging purposes (replace with proper logging framework)
        print(f"Error importing API specification: {e}")  # Replace with logger.error()
        raise HTTPException(status_code=500, detail="Internal server error.")