import os
import urllib.parse
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# --- Database Credentials ---
DB_USER = os.environ.get("DB_USER", "postgres")
raw_pass = os.environ.get("DB_PASS", "default_password")
DB_PASS = urllib.parse.quote_plus(raw_pass)
DB_NAME = os.environ.get("DB_NAME", "fintrack")
PUBLIC_IP = os.environ.get("PUBLIC_IP", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "5432")

# --- AI Credentials ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Error: GOOGLE_API_KEY environment variable not set or empty.")

# --- Frontend Configuration ---
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]
