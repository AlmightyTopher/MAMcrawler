
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Explicitly load .env
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(dotenv_path)

from sqlalchemy import create_engine
from backend.database import Base
from backend.config import get_settings
from backend.models import * # Import all models to ensure they are registered

def update_schema():
    settings = get_settings()
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    print("Creating missing tables...")
    Base.metadata.create_all(engine)
    print("Schema updated.")

if __name__ == "__main__":
    update_schema()
