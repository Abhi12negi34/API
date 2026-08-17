import logging
from typing import List, Tuple

from src.backend.tests.locator_strategy import LocatorStrategy  # Assuming this module exists as per dependencies
# from MOD-019 import some_function # Example dependency interaction - remove if unused

logger = logging.getLogger(__name__)


class SelfHealingTest:
    """
    Implements self-healing capabilities within API tests to adapt to minor UI changes.
    Handles dynamically loaded content and attempts to adjust locators when elements are not found.
    """

    def __init__(self, max_locator_adjustments=3):
        """
        Initializes the SelfHealingTest with a maximum number of locator adjustments allowed per test.
        """
        self.max_locator_adjustments = max_locator_adjustments
        self.adjustment_attempts = 0

    def find_element(self, driver, locator: Tuple[str, str], strategy: LocatorStrategy = LocatorStrategy.XPATH):
        """
        Attempts to locate an element using the given locator and strategy.  If not found, it attempts self-healing.

        Args:
            driver: The Selenium WebDriver instance.
            locator (Tuple[str, str]): A tuple containing the locator type and value.
            strategy (LocatorStrategy): The Locator Strategy used for locating the element.

        Returns:
            The WebElement if found, otherwise None.  Logs failed attempts.
        """
        try:
            element = driver.find_element(strategy.value, locator[1])
            return element
        except Exception as e:
            if self.adjustment_attempts < self.max_locator_adjustments:
                self._attempt_heal(driver, locator)
                # Recursively call find_element after healing attempt
                return self.find_element(driver, locator, strategy)

            else:
                logger.error(f"Failed to locate element after {self.max_locator_adjustments} adjustment attempts.")
                logger.exception(e) # Log the original exception for debugging
                return None  # Or raise an exception if immediate failure is preferred

    def _attempt_heal(self, driver, locator: Tuple[str, str]):
        """
        Attempts to heal a broken locator by suggesting alternatives.
        This is a placeholder - more sophisticated healing logic would go here.
        Currently implements a simple fallback strategy of trying different attributes.

        Args:
            driver: The Selenium WebDriver instance.
            locator (Tuple[str, str]): The original locator.
        """
        self.adjustment_attempts += 1
        logger.warning(f"Attempting to heal locator: {locator}")

        # Example healing strategy - try a different attribute
        if locator[0] == LocatorStrategy.XPATH: # Avoid infinite loop if already using CSS Selector
            try:
                # Attempt to find the element by its ID first
                element = driver.find_element(LocatorStrategy.ID, locator[1])
                logger.info(f"Healed locator by switching to ID: {locator[1]}")

            except Exception as e:
                # If still not found, try other attributes (e.g., name) - implement more strategies here
                try:
                     element = driver.find_element(LocatorStrategy.NAME, locator[1])
                     logger.info(f"Healed locator by switching to Name: {locator[1]}")

                except Exception as e2:

                    logger.warning("Healing attempt failed.") #Log if healing fails on all attempts




if __name__ == '__main__':
    # Example Usage (for demonstration - remove in production)
    logging.basicConfig(level=logging.INFO)  # Set log level to INFO

    class MockWebDriver: #Mock driver for testing, replace with actual webdriver when used in tests
        def find_element(self, strategy, value):
            if value == "some_missing_element":
                raise Exception("Element not found")
            else:
                return f"Found element at {value}"

    mock_driver = MockWebDriver()
    healing_test = SelfHealingTest(max_locator_adjustments=2)
    locator = (LocatorStrategy.XPATH, "some_missing_element")
    element = healing_test.find_element(mock_driver, locator)

    if element:
        print(f"Element found: {element}")
    else:
        print("Element not found even after healing attempts.")