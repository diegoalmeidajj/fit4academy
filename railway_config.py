import os

IS_RAILWAY = bool(os.getenv('RAILWAY_ENVIRONMENT'))
RAILWAY_DATABASE_URL = os.getenv('DATABASE_URL', '')
