from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
# import os # Temporarily remove os import
# from dotenv import load_dotenv # Temporarily remove dotenv import

# Temporarily disable all .env loading and os.getenv
# load_dotenv()

# --- TEMPORARY HARDCODED URL FOR ALEMBIC --- 
db_url_to_use = "mysql+mysqlconnector://root:%2B1826%2BDark@localhost:3306/inp"
print(f"[app/database.py] USING ABSOLUTELY HARDCODED DATABASE_URL: {db_url_to_use}")

engine = create_engine(db_url_to_use, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency for creating session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
