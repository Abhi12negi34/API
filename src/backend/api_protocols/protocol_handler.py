from src.backend.api_protocols import rest_adapter, soap_adapter

import json
import grpc
from google.protobuf.json_format import MessageToJson

class ProtocolHandler:
    """
    Handles the reception and translation of diverse API protocols into a standardized internal format.
    Supports REST, SOAP, and gRPC.
    """

    def __init__(self):
        pass

    def handle_request(self, protocol, message, payload=None):
        """
        Routes the request to the appropriate adapter based on the protocol.

        Args:
            protocol (str): The API protocol being used (e.g., "REST", "SOAP", "gRPC").
            message (str or object):  The incoming message. This can be a string for REST/SOAP, 
                                        or a gRPC request object.
            payload (bytes, optional): For REST and SOAP, the payload bytes. Defaults to None.

        Returns:
            dict: The standardized internal format of the processed request.  Returns an error dictionary on failure.
        """
        try:
            if protocol.upper() == "REST":
                return rest_adapter.adapt_rest(message, payload)
            elif protocol.upper() == "SOAP":
                return soap_adapter.adapt_soap(message, payload)
            elif protocol.upper() == "GRPC":
                 return self._handle_grpc(message)
            else:
                return {"error": "Unsupported protocol"}, 400  # Bad Request
        except Exception as e:
            print(f"Error handling request: {e}") # Log for debugging. In production, use a proper logger
            return {"error": str(e)}, 500 # Internal Server Error

    def _handle_grpc(self, request):
        """Handles gRPC requests."""
        try:
            # Assuming 'request' is already the gRPC service object and method called.
            # Adapt as needed based on your gRPC setup.  This example converts to JSON for standardization.
            if hasattr(request, 'to_json'): # Check if the request has a to_json method
                json_data = MessageToJson(request)
                return json.loads(json_data)
            else:
                 return {"error": "gRPC message does not have necessary conversion methods."}, 500

        except Exception as e:
            print(f"Error handling gRPC request: {e}")
            return {"error": str(e)}, 500
        


if __name__ == '__main__':
    # Example usage (for testing)
    handler = ProtocolHandler()

    # REST example
    rest_message = 'GET /api/data'
    rest_payload = b'{"key":"value"}'
    rest_response = handler.handle_request("REST", rest_message, rest_payload)
    print(f"REST Response: {rest_response}")

    # SOAP example
    soap_message = '<Envelope><Body><RequestData>Some data</RequestData></Body></Envelope>'
    soap_payload = b'<?xml version="1.0"?>...' # Replace with actual SOAP payload
    soap_response = handler.handle_request("SOAP", soap_message, soap_payload)
    print(f"SOAP Response: {soap_response}")

    # gRPC example (mock - replace with actual gRPC setup and message)
    class MockGRPCMessage:  #Mock for test purposes only
        def __init__(self):
            self.field1 = "test data"
        def to_json(self):
            return '{"field1": "test data"}'

    grpc_message = MockGRPCMessage() # Replace with actual gRPC request object
    grpc_response = handler.handle_request("gRPC", grpc_message)
    print(f"gRPC Response: {grpc_response}")

    #Error handling test - invalid protocol
    error_response = handler.handle_request("INVALID", "some message")
    print(f"Error Response: {error_response}")