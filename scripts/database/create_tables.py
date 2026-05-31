import sys
from pathlib import Path

# Ensure app imports resolve when this script is run by path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import Base, engine
from app import models  # This will import all models

print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")

print("\nList of tables created:")
from sqlalchemy import inspect
inspector = inspect(engine)
for table_name in inspector.get_table_names():
    print(f"- {table_name}")
