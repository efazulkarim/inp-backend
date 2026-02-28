#!/usr/bin/env python3
"""
Script to set up a fresh database by creating all tables and stamping migrations
This is useful when migrating to a new database or setting up from scratch
"""
import sys
from app.database import Base, engine
from app import models  # This will import all models
from sqlalchemy import inspect

def setup_database():
    print("=" * 60)
    print("Setting up fresh database...")
    print("=" * 60)
    
    # Step 1: Create all tables
    print("\n1. Creating all tables from models...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    # Step 2: List created tables
    print("\n2. Verifying created tables...")
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Found {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
    except Exception as e:
        print(f"⚠️  Warning: Could not list tables: {e}")
    
    # Step 3: Stamp database with latest migration
    print("\n3. Stamping database with latest migration...")
    print("   (This marks all migrations as applied without running them)")
    print("   Run: alembic stamp head")
    print("\n✅ Database setup complete!")
    print("\nNext step: Run 'alembic stamp head' to mark all migrations as applied")
    
    return True

if __name__ == "__main__":
    if setup_database():
        print("\n" + "=" * 60)
        print("Setup completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Setup failed. Please check the errors above.")
        print("=" * 60)
        sys.exit(1)