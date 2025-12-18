
import os
import sys
from sqlalchemy import create_engine, text

# Try different connection strings
configs = [
    "postgresql://postgres:postgres@localhost:5432/audiobooks",
    "postgresql://postgres:password@localhost:5432/audiobooks",
    "postgresql://postgres:your_postgres_password@localhost:5432/audiobooks",
    "postgresql://postgres:@localhost:5432/audiobooks",  # No password
    "postgresql://audiobook_user:audiobook_password@localhost:5432/audiobook_automation", # Default
]

def probe():
    for url in configs:
        print(f"Testing: {url}")
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print(f"SUCCESS! Connected to {url}")
                return url
        except Exception as e:
            print(f"Failed: {e}")
    return None

if __name__ == "__main__":
    probe()
