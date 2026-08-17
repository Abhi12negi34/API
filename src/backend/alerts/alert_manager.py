import logging
from prometheus_client import Gauge, Summary
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define Prometheus metrics
REQUEST_LATENCY = Gauge('api_request_latency_seconds', 'Latency of API requests')
ERROR_RATE = Gauge('api_error_rate', 'Rate of errors in API requests')
THROUGHPUT = Gauge('api_throughput', 'Number of API requests per second')
ALERT_FIRE_COUNT = Summary('alert_fire_count', 'Count of times alerts have fired.')


class AlertManager:
    """
    Manages alerts based on API metrics.
    """

    def __init__(self, alert_config):
        """
        Initializes the AlertManager with alert configurations.

        Args:
            alert_config (dict): A dictionary containing alert thresholds for different severities.
                                 Example: {'high': {'latency': 1.0, 'error_rate': 0.1},
                                           'medium': {'latency': 0.5, 'error_rate': 0.05}}
        """
        self.alert_config = alert_config
        self.alerts = []

    def check_metrics(self, latency, error_rate, throughput):
        """
        Checks API metrics against configured thresholds and triggers alerts if necessary.

        Args:
            latency (float): The latency of the API request.
            error_rate (float): The error rate of the API request.
            throughput (int): The throughput of the API request.
        """
        for severity, thresholds in self.alert_config.items():
            if latency > thresholds.get('latency', float('inf')):
                self._trigger_alert(f"High Latency ({severity}): Latency is {latency:.2f}s (threshold: {thresholds.get('latency', float('inf'))})")
            if error_rate > thresholds.get('error_rate', float('inf')):
                self._trigger_alert(f"High Error Rate ({severity}): Error rate is {error_rate:.2%} (threshold: {thresholds.get('error_rate', float('inf'))})")
            if throughput < thresholds.get('throughput', 0):
                 self._trigger_alert(f"Low Throughput ({severity}): Throughput is {throughput} (threshold: {thresholds.get('throughput', 0)})")

        # Update Prometheus metrics even if no alerts are fired.  This helps with visualization and historical data.
        REQUEST_LATENCY.set(latency)
        ERROR_RATE.set(error_rate)
        THROUGHPUT.set(throughput)


    def _trigger_alert(self, message):
        """
        Triggers an alert and logs the event.  Also updates Prometheus summary metric for fired alerts.

        Args:
            message (str): The alert message.
        """
        try:
            # Simulate sending a notification (e.g., to email, Slack)
            print(f"ALERT: {message}")
            self.alerts.append({"message": message, "severity": self._extract_severity(message)})
            ALERT_FIRE_COUNT.inc() #Increment Prometheus metric

        except Exception as e:
            logging.error(f"Failed to send alert: {e}")


    def _extract_severity(self, message):
       """Extracts severity from the alert message."""
       if "high" in message.lower():
           return "high"
       elif "medium" in message.lower():
           return "medium"
       else:
           return "low"


    def get_alerts(self):
        """
        Retrieves a list of recent alerts.

        Returns:
            list: A list of dictionaries, each representing an alert with its message and severity.
        """
        return self.alerts