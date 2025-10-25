import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./.chroma")
USER_ID = os.getenv("USER_ID", "demo")
COMMIT_POLL_SECONDS = int(os.getenv("COMMIT_POLL_SECONDS", "60"))
COMMIT_MAX = int(os.getenv("COMMIT_MAX", "40"))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
LAST_RECO_PATH = os.path.join(DATA_DIR, "last_reco.json")

# DoorDash
DOORDASH_DEVELOPER_ID = os.getenv("DOORDASH_DEVELOPER_ID", "")
DOORDASH_KEY_ID = os.getenv("DOORDASH_KEY_ID", "")
DOORDASH_SIGNING_SECRET = os.getenv("DOORDASH_SIGNING_SECRET", "")  # base64url string from portal
DOORDASH_BASE = os.getenv("DOORDASH_BASE", "https://openapi.doordash.com")