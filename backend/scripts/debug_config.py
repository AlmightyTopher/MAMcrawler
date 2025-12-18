
import os
import sys
from dotenv import load_dotenv

# Print current CWD
print(f"CWD: {os.getcwd()}")
print(f"Files in CWD: {os.listdir('.')}")

# Check .env content manually
try:
    with open('.env') as f:
        print(".env content (partial):")
        for line in f.readlines():
            if "DATABASE_URL" in line:
                print(f"Found: {line.strip()}")
except Exception as e:
    print(f"Could not read .env: {e}")

# Load via dotenv directly to see if that works
load_dotenv()
print(f"os.getenv('DATABASE_URL'): {os.getenv('DATABASE_URL')}")

# Add path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.config import get_settings

settings = get_settings()
print(f"Settings.DATABASE_URL: {settings.DATABASE_URL}")
