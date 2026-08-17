from typing import List, Optional

class VersionManager:
    """
    Manages API versions and their associated test cases.
    Handles API deprecation scenarios and parallel deployments.
    """

    def __init__(self):
        self.supported_versions = ["v1", "v2"]  # Add supported versions here
        self.deprecated_versions = [] #Versions marked for deprecation
        self.version_test_map = {} # Maps API version to list of test case IDs

    def add_version(self, version: str):
        """Adds a new API version."""
        if version not in self.supported_versions:
            self.supported_versions.append(version)

    def deprecate_version(self, version: str):
         """Marks an API version as deprecated"""
         if version in self.supported_versions and version not in self.deprecated_versions:
            self.deprecated_versions.append(version)
            print(f"API Version {version} marked for deprecation.")
         else:
            raise ValueError(f"Version {version} is either already deprecated or not supported.")

    def get_supported_versions(self) -> List[str]:
        """Returns a list of currently supported API versions."""
        return self.supported_versions

    def associate_test_with_version(self, test_id: int, version: str):
        """Associates a test case with a specific API version."""
        if version not in self.supported_versions:
            raise ValueError(f"API version '{version}' does not exist.")

        if version not in self.version_test_map:
            self.version_test_map[version] = []
        self.version_test_map[version].append(test_id)

    def get_tests_for_version(self, version: str) -> List[int]:
        """Returns a list of test case IDs associated with a specific API version."""
        if version not in self.supported_versions:
            raise ValueError(f"API version '{version}' does not exist.")

        return self.version_test_map.get(version, []) # Return empty list if no tests are assigned to this version
    
    def validate_api_version(self, api_version: str) -> bool:
         """Validates if the provided API version is supported."""
         return api_version in self.supported_versions

    def handle_parallel_deployments(self, requested_version:str):
        """Handles parallel deployments of different API versions by routing requests to the correct logic."""
        if not self.validate_api_version(requested_version):
            raise ValueError(f"Unsupported API version: {requested_version}")

        # In a real application this would involve request routing or similar mechanisms 
        print(f"Routing request to API Version {requested_version}.")

    def get_deprecated_versions(self) -> List[str]:
        """Returns a list of deprecated versions."""
        return self.deprecated_versions