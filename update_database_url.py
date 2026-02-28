#!/usr/bin/env python3
"""
Script to update DATABASE_URL in .env file for PostgreSQL migration
"""
import os
import sys

def update_database_url():
    """
    Update the DATABASE_URL in .env file with the new PostgreSQL connection string
    """
    # New PostgreSQL connection string (Neon.tech)
    new_db_url = "postgresql://neondb_owner:npg_8kZOpRqcozg5@ep-steep-cell-a1vd4jdx-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    
    # Check for .env file in different locations
    env_paths = [
        '.env',  # Root directory
        os.path.join('app', '.env'),  # App directory
    ]
    
    env_path = None
    for path in env_paths:
        if os.path.exists(path):
            env_path = path
            break
    
    if not env_path:
        print("Error: Could not find .env file.")
        return False
    
    # Read the current .env file
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update DATABASE_URL if it exists
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('DATABASE_URL='):
            lines[i] = f"DATABASE_URL={new_db_url}\n"
            updated = True
            break
    
    # If DATABASE_URL doesn't exist, add it
    if not updated:
        lines.append(f"DATABASE_URL={new_db_url}\n")
    
    # Write the updated .env file
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    print(f"Successfully updated DATABASE_URL in {env_path}")
    print(f"New DATABASE_URL: {new_db_url}")
    return True

if __name__ == "__main__":
    if update_database_url():
        print("\nDatabase URL updated successfully!")
        print("\nNext steps:")
        print("1. Install the PostgreSQL driver: pip install psycopg2-binary")
        print("2. Run database migrations: alembic upgrade head")
        print("3. Restart your application")
    else:
        print("Failed to update database URL")
        sys.exit(1)
