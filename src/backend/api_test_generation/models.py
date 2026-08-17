from typing import List, Optional

class ApiSpecMetadata(object):
    """Represents metadata about an API specification."""

    def __init__(self, api_spec_id: str, content: str):
        """
        Initializes the ApiSpecMetadata object.

        Args:
            api_spec_id (str): The unique identifier of the API specification.
            content (str): The OpenAPI specification content (e.g., YAML or JSON).
        """
        self.api_spec_id = api_spec_id
        self.content = content

class TestCaseGenerationRequest(object):
    """Represents a request to generate test cases."""

    def __init__(self, api_spec_id: str):
        """
        Initializes the TestCaseGenerationRequest object.

        Args:
            api_spec_id (str): The ID of the API specification for which to generate test cases.
        """
        self.api_spec_id = api_spec_id

class TestCaseGenerationResponse(object):
    """Represents the response from a test case generation request."""

    def __init__(self, test_case_ids: List[str]):
        """
        Initializes the TestCaseGenerationResponse object.

        Args:
            test_case_ids (List[str]): A list of IDs for the generated test cases.
        """
        self.test_case_ids = test_case_ids

class GenerationError(Exception):
    """Custom exception for generation-related errors."""
    pass

class InvalidApiSpecError(GenerationError):
    """Raised when the API specification is invalid or malformed."""
    def __init__(self, message: str, api_spec_id: Optional[str] = None):
        super().__init__(message)
        self.api_spec_id = api_spec_id

class AiError(GenerationError):
    """Raised when there's an error during AI processing."""
    def __init__(self, message: str):
        super().__init__(message)