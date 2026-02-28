import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

def test_connection():
    print("Attempting to load .env file...")
    # Try multiple possible locations for the .env file (same logic as app/database.py)
    possible_env_paths = [
        os.path.join(os.path.dirname(__file__), '.env'),  # project root
        os.path.join(os.path.dirname(__file__), 'app', '.env'),  # app directory
        '.env'  # current working directory
    ]
    
    env_path_loaded = None
    for env_path in possible_env_paths:
        if os.path.exists(env_path):
            print(f"💡 Found .env file at: {env_path}")
            load_dotenv(dotenv_path=env_path, verbose=True)
            env_path_loaded = env_path
            break
    
    if not env_path_loaded:
        print("⚠️ WARNING: No .env file found in any standard location!")
        print("Tried paths:", possible_env_paths)
    else:
        print(f"✅ Loaded .env from: {env_path_loaded}")
    
    database_url = os.getenv("DATABASE_URL")
    
    # Strip quotes if present (python-dotenv should handle this, but just in case)
    if database_url:
        database_url = database_url.strip().strip('"').strip("'")

    print(f"DATABASE_URL from os.getenv: '{database_url}'")

    if not database_url:
        print("Error: DATABASE_URL environment variable not found.")
        print("Please ensure your .env file is correctly set up with:")
        print("DATABASE_URL=\"postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME\"")
        return

    print(f"Attempting to connect to: {database_url}")

    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            # Optional: Execute a simple query to confirm connectivity
            result = connection.execute(text("SELECT 1"))
            for row in result:
                print(f"Successfully connected to the database and executed a test query. Result: {row}")
            print("Database connection successful!")
    except SQLAlchemyError as e:
        print(f"Error connecting to the database: {e}")
        print("Please check:")
        print("1. Your PostgreSQL server is running and accessible.")
        print("2. The DATABASE_URL in your .env file is correct (driver, username, password, host, port, database name).")
        print("   Example: postgresql://user:pass@host:5432/dbname")
        print("3. The specified database exists in your PostgreSQL server.")
        print("4. The user has the correct privileges for the database.")
        print("5. The 'psycopg2-binary' library is correctly installed in your virtual environment.")
    except ImportError as e:
        print(f"ImportError: {e}. This might indicate the 'psycopg2-binary' or 'python-dotenv' library is not installed correctly.")

if __name__ == "__main__":
    test_connection()