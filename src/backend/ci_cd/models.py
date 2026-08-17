from typing import Optional
import uuid

class TestExecutionRequest:
    def __init__(self, pipeline_id: str, test_suite_id: str):
        if not isinstance(pipeline_id, str) or not pipeline_id:
            raise ValueError("Pipeline ID must be a non-empty string.")
        if not isinstance(test_suite_id, str) or not test_suite_id:
            raise ValueError("Test Suite ID must be a non-empty string.")

        self.pipeline_id = pipeline_id
        self.test_suite_id = test_suite_id


class TestExecutionResult:
    def __init__(self, execution_id: str):
        if not isinstance(execution_id, str) or not execution_id:
            raise ValueError("Execution ID must be a non-empty string.")
        self.execution_id = execution_id

    def to_dict(self):
        return {"execution_id": self.execution_id}


class CIIntegrationError(Exception):
    """Base class for CI/CD integration errors."""
    pass


class TriggerFailedError(CIIntegrationError):
    """Raised when test triggering fails."""
    def __init__(self, message: str):
        super().__init__(message)

class TimeoutError(CIIntegrationError):
    """Raised when a timeout occurs during test execution."""
    def __init__(self, message: str):
        super().__init__(message)


def generate_execution_id() -> str:
    """Generates a unique execution ID using UUID."""
    return str(uuid.uuid4())