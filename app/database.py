from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load .env file from the project root, assuming this script might be called from elsewhere
# Or ensure .env is loaded before this module by the main application
# For Alembic, env.py should handle its own DB URL loading from alembic.ini or env vars

# Determine the base directory of the project
# This assumes database.py is in app/ and .env is in the root
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
    # print(f"[app/database.py] Loaded .env from: {DOTENV_PATH}") # Optional debug
# else:
    # print(f"[app/database.py] .env file not found at {DOTENV_PATH}") # Optional debug

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    print("[app/database.py] CRITICAL ERROR: DATABASE_URL environment variable not set.")
    # Potentially raise an error or use a default for local dev if absolutely necessary,
    # but for deployment, it should always be set.
    # For now, let's keep the previous hardcoded one as an ultimate fallback for safety,
    # but with a strong warning if it's used.
    SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root:%2B1826%2BDark@localhost:3306/inp" # Fallback
    print(f"[app/database.py] WARNING: Using HARDCODED FALLBACK DATABASE_URL: {SQLALCHEMY_DATABASE_URL}")
# else:
    # print(f"[app/database.py] Using DATABASE_URL from environment: {SQLALCHEMY_DATABASE_URL}") # Optional debug

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()