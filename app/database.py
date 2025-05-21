from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# More robust .env file loading, similar to other services
# Try multiple possible locations for the .env file
# This assumes database.py is in the 'app' directory.
possible_env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),  # project root (app -> project_root)
    os.path.join(os.path.dirname(__file__), '.env'),  # app directory (less common for global .env)
    '.env'  # current working directory (if script/alembic run from root)
]

env_path_loaded = None
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        print(f"[app/database.py] 💡 Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_path_loaded = env_path
        break

if not env_path_loaded:
    print("[app/database.py] ⚠️ WARNING: No .env file found in any standard location!")
# else:
    # print(f"[app/database.py] Loaded .env from: {env_path_loaded}") # Optional debug confirmation

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    print("[app/database.py] CRITICAL ERROR: DATABASE_URL environment variable not set after attempting to load .env.")
    # Potentially raise an error or use a default for local dev if absolutely necessary,
    # but for deployment, it should always be set.
    # For now, let's keep the previous hardcoded one as an ultimate fallback for safety,
    # but with a strong warning if it's used.
    SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root:%2B1826%2BDark@localhost:3306/inp" # Fallback
    print(f"[app/database.py] WARNING: Using HARDCODED FALLBACK DATABASE_URL: {SQLALCHEMY_DATABASE_URL}")
else:
    print(f"[app/database.py] ✅ Using DATABASE_URL from environment (loaded from {env_path_loaded if env_path_loaded else 'system env'}).")

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()