import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

def test_connection():
    print("Attempting to load .env file...")
    loaded_successfully = load_dotenv(verbose=True)
    print(f".env file loaded: {loaded_successfully}")
    database_url = os.getenv("DATABASE_URL")

    print(f"DATABASE_URL from os.getenv: '{database_url}'")

    if not database_url:
        print("Error: DATABASE_URL environment variable not found.")
        print("Please ensure your .env file is correctly set up with:")
        print("DATABASE_URL=\"mysql+mysqlclient://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME\"")
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
        print("1. Your MySQL server is running.")
        print("2. The DATABASE_URL in your .env file is correct (driver, username, password, host, port, database name).")
        print("   Example: mysql+mysqlclient://user:pass@localhost:3306/mydb")
        print("3. The specified database exists in your MySQL server.")
        print("4. The user has the correct privileges for the database.")
        print("5. The 'mysqlclient' library is correctly installed in your virtual environment.")
    except ImportError as e:
        print(f"ImportError: {e}. This might indicate the 'mysqlclient' or 'python-dotenv' library is not installed correctly.")

if __name__ == "__main__":
    test_connection()