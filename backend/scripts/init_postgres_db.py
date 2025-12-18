
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Connect to 'postgres' system db
url = "postgresql://postgres:postgres@localhost:5432/postgres"

def create_app_db():
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            # Check if db exists
            result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'audiobooks'"))
            if result.fetchone():
                print("Database 'audiobooks' already exists.")
            else:
                conn.execute(text("CREATE DATABASE audiobooks"))
                print("Created database 'audiobooks'.")
    except Exception as e:
        print(f"Failed to create DB: {e}")

if __name__ == "__main__":
    create_app_db()
