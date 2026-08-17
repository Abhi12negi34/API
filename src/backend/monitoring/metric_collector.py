import time
import logging
from prometheus_client import Summary, Gauge

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define Prometheus metrics
REQUEST_LATENCY = Summary('api_request_latency', 'API request latency in seconds')
ERROR_RATE = Gauge('api_error_rate', 'Rate of API errors')
THROUGHPUT = Gauge('api_throughput', 'Number of API requests processed')


class MetricCollector:
    """
    Collects API metrics and triggers alerts based on defined thresholds.
    """

    def __init__(self, alert_manager):
        """
        Initializes the MetricCollector with an AlertManager instance for triggering alerts.
        """
        self.alert_manager = alert_manager
        self.thresholds = {
            'latency': 0.5,  # seconds
            'error_rate': 0.1,  # percentage
            'throughput': 100  # requests per minute
        }

    def collect_metrics(self, latency, error_count, request_count):
        """
        Collects metrics and triggers alerts if thresholds are breached.

        Args:
            latency (float): The API request latency in seconds.
            error_count (int): The number of API errors.
            request_count (int): The total number of API requests.
        """
        try:
            with REQUEST_LATENCY.time():
                # Simulate some work being done to calculate metrics and trigger alerts.
                pass

            REQUEST_LATENCY.observe(latency)

            error_rate = error_count / request_count if request_count > 0 else 0
            ERROR_RATE.set(error_rate)
            THROUGHPUT.inc(request_count)

            self._check_alerts(latency, error_rate, request_count)

        except Exception as e:
            logging.error(f"Error collecting metrics: {e}")
            # Implement retry mechanism if necessary


    def _check_alerts(self, latency, error_rate, request_count):
        """
        Checks if any alerts need to be triggered based on the collected metrics.

        Args:
            latency (float): The API request latency in seconds.
            error_rate (float): The API error rate.
            request_count (int): The total number of API requests.
        """
        if latency > self.thresholds['latency']:
            self._trigger_alert("High Latency", "warning", f"API latency is high: {latency:.2f} seconds")

        if error_rate > self.thresholds['error_rate']:
            self._trigger_alert("High Error Rate", "critical", f"API error rate is high: {error_rate:.2f}")

        # Check throughput (e.g., if it drops below a certain level).  Adjust threshold as needed.
        if request_count < self.thresholds['throughput']:
            self._trigger_alert("Low Throughput", "warning", f"API throughput is low: {request_count} requests")

    def _trigger_alert(self, alert_name, severity, message):
        """
        Triggers an alert using the AlertManager.

        Args:
            alert_name (str): The name of the alert.
            severity (str): The severity of the alert (e.g., "warning", "critical").
            message (str): The alert message.
        """
        try:
            self.alert_manager.send_alert(message, severity)  # Assuming send_alert takes message and severity
            logging.info(f"Alert triggered: {alert_name} - Severity: {severity} - Message: {message}")

        except Exception as e:
            logging.error(f"Failed to trigger alert: {alert_name}. Error: {e}")



if __name__ == '__main__':
    # Mock AlertManager for testing (replace with actual implementation)
    class MockAlertManager:
        def send_alert(self, message, severity):
            print(f"Mock Alert: Severity={severity}, Message={message}")

    alert_manager = MockAlertManager()
    metric_collector = MetricCollector(alert_manager)

    # Simulate API requests and collect metrics
    for i in range(100):
        latency = 0.2 + (i % 5 * 0.1)  # Vary latency to test alerts
        error_count = int(i % 10 == 0)  # Introduce some errors
        request_count = 1

        metric_collector.collect_metrics(latency, error_count, request_count)
        time.sleep(0.1) # simulate requests coming in over time