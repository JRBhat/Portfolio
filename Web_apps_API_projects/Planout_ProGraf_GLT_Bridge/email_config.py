import os

EMAIL_CONFIG = {
    'smtp_server': os.environ.get("SMTP_SERVER", "localhost"),  # internal SMTP relay
    'smtp_port': 25,
    'sender_email': os.environ.get("SENDER_EMAIL", "sender@example.com"),
}
