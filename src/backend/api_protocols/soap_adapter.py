from lxml import etree
import logging

logger = logging.getLogger(__name__)

class SoapAdapter:
    """
    Adapts SOAP requests to a standardized internal format.  Handles input validation,
    malformed messages, and potentially large payloads.
    """

    def __init__(self):
        pass

    def parse_soap(self, soap_message):
        """
        Parses the incoming SOAP message and extracts relevant data.

        Args:
            soap_message (str): The raw SOAP XML string.

        Returns:
            dict: A dictionary representing the parsed SOAP message in a standardized format,
                  or None if parsing fails.  Returns an empty dict for empty payloads.

        Raises:
            ValueError: If the input is not valid XML or has unexpected structure.
        """
        try:
            root = etree.fromstring(soap_message.encode('utf-8')) #Handles string to bytes conversion
        except etree.XMLSyntaxError as e:
            logger.error(f"Invalid SOAP message format: {e}")
            raise ValueError("Invalid XML syntax in SOAP message") from e

        # Basic validation: Check for expected root element (adjust namespace if necessary)
        if root.tag == 'soapenv:Envelope':  # Example Namespace check
             body = root.find('./soapenv:Body') # Find the body
             if body is None:
                 logger.warning("SOAP message has no Body.")
                 return {}

             operation_name = None
             payload = {}

             for child in body:
                # Assuming one operation per SOAP request for simplicity. Adapt if multiple operations are allowed.
                if len(child) > 0 :
                    operation_name = child.tag #Assuming Tag Name to be the Operation Name
                    for item in child:
                        payload[item.tag] = item.text
                else:
                   operation_name = child.tag
                   payload[child.tag] = child.text

             if not operation_name :
                 logger.error("SOAP message has no valid Operation Name.")
                 raise ValueError("SOAP message does not contain a recognizable operation.")


             return {"operation": operation_name, "payload": payload}
        else:
            logger.error(f"Unexpected SOAP root element: {root.tag}")
            raise ValueError(f"Unexpected SOAP Root Element: {root.tag}. Expected soapenv:Envelope")

    def adapt_request(self, request):
        """
        Adapts a SOAP request to the internal standardized format.

        Args:
            request (str): The raw SOAP XML string representing the request.

        Returns:
            dict: A dictionary containing the adapted request data, or None if adaptation fails.

        Raises:
            ValueError: For invalid requests (e.g., malformed XML).
            Exception: Propagate other exceptions as needed.
        """

        try:
             parsed_soap = self.parse_soap(request)
             if parsed_soap is None:
                 raise ValueError("Failed to parse SOAP message.")
             return parsed_soap
        except ValueError as e:
            logger.exception(f"Error adapting SOAP request: {e}") # log exception with stack trace
            raise e
        except Exception as e :
            logger.exception(f"Unexpected error during SOAP adaptation: {e}")
            raise

    def validate_input(self, data):
        """
        Validates the input data before processing.  This is a placeholder - 
        implement more robust validation based on specific requirements.

        Args:
            data (dict): The dictionary representing the request payload.

        Returns:
            bool: True if the data is valid, False otherwise.
        """

        if not isinstance(data, dict):
            logger.error("Input must be a dictionary.")
            return False

        # Example validation: Check for required keys (adapt to your use case)
        if "operation" not in data or "payload" not in data:
             logger.error("Missing 'operation' or 'payload' key in SOAP Data")
             return False

        return True