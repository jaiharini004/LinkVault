import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Use SQLite as fallback if DATABASE_URL is not set
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///linkvault.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
