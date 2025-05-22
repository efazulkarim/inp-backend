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