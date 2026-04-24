import os
from dotenv import load_dotenv
load_dotenv()

_IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production' or bool(os.getenv('RAILWAY_ENVIRONMENT'))

SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if _IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY environment variable is required in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    SECRET_KEY = 'dev-only-insecure-key-do-not-use-in-production'

DATABASE_URL = os.getenv('DATABASE_URL', '')
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'academy.db')
PORT = int(os.getenv('PORT', 8080))

# SMTP
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')

# Stripe
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Square
SQUARE_ACCESS_TOKEN = os.getenv('SQUARE_ACCESS_TOKEN', '')
SQUARE_LOCATION_ID = os.getenv('SQUARE_LOCATION_ID', '')
SQUARE_ENVIRONMENT = os.getenv('SQUARE_ENVIRONMENT', 'sandbox')

# Cloudinary
CLOUDINARY_URL = os.getenv('CLOUDINARY_URL', '')

# Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE = os.getenv('TWILIO_PHONE', '')
