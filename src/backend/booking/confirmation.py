import logging
import time
from smtplib import SMTPException
from typing import Dict, Any

from MOD_012 import notification

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def confirm_booking(booking_details: Dict[str, Any]) -> bool:
    """
    Confirms a booking by sending email and SMS notifications to the user.

    Args:
        booking_details: A dictionary containing booking details, 
                         including user email, phone number, and booking information.

    Returns:
        True if confirmation was successful, False otherwise.
    """
    try:
        user_email = booking_details.get('user_email')
        user_phone = booking_details.get('user_phone')
        booking_info = booking_details.get('booking_info')
        opt_out_email = booking_details.get('opt_out_email', False)
        opt_out_sms = booking_details.get('opt_out_sms', False)

        if not user_email and not user_phone:
            logging.warning("No email or phone number provided for confirmation.")
            return False

        # Send confirmation email
        if user_email and not opt_out_email:
            try:
                email_subject = "Booking Confirmation"
                email_body = f"Your booking is confirmed:\n{booking_info}"
                notification.send_email(user_email, email_subject, email_body)
                logging.info(f"Confirmation email sent to {user_email}")
            except SMTPException as e:
                logging.error(f"Failed to send confirmation email to {user_email}: {e}")
                # Retry mechanism
                retry_email(user_email, email_subject, email_body)
                
        # Send confirmation SMS
        if user_phone and not opt_out_sms:
            try:
                sms_message = f"Your booking is confirmed: {booking_info}"
                notification.send_sms(user_phone, sms_message)
                logging.info(f"Confirmation SMS sent to {user_phone}")
            except Exception as e:
                logging.error(f"Failed to send confirmation SMS to {user_phone}: {e}")
                # Retry mechanism
                retry_sms(user_phone, sms_message)
        
        return True

    except Exception as e:
        logging.exception(f"An unexpected error occurred during booking confirmation: {e}")
        return False

def retry_email(email: str, subject: str, body: str, max_retries: int = 3, delay: int = 5):
    """Retries sending an email after a delay."""
    for attempt in range(max_retries):
        try:
            notification.send_email(email, subject, body)
            logging.info(f"Email retry {attempt + 1} successful to {email}")
            return
        except SMTPException as e:
            logging.error(f"Email retry {attempt + 1} failed to {email}: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)

def retry_sms(phone: str, message: str, max_retries: int = 3, delay: int = 5):
    """Retries sending an SMS after a delay."""
    for attempt in range(max_retries):
        try:
            notification.send_sms(phone, message)
            logging.info(f"SMS retry {attempt + 1} successful to {phone}")
            return
        except Exception as e:
            logging.error(f"SMS retry {attempt + 1} failed to {phone}: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)