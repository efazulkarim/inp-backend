import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import your models here. Crucially, import SQLALCHEMY_DATABASE_URL
# from app.database.py which has the robust .env loading.
from app.database import Base, SQLALCHEMY_DATABASE_URL
from app import models  # This will import all models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Set the sqlalchemy.url in the Alembic config *before* it's used by engine_from_config.
# This ensures that the DATABASE_URL loaded from .env by app/database.py is used.
if SQLALCHEMY_DATABASE_URL:
    print(f"[alembic/env.py] 💡 Original sqlalchemy.url from app.database: {SQLALCHEMY_DATABASE_URL}")
    # Escape '%' for configparser by replacing it with '%%'
    escaped_db_url = SQLALCHEMY_DATABASE_URL.replace('%', '%%')
    print(f"[alembic/env.py] 💡 Setting Alembic's sqlalchemy.url (escaped for configparser): {escaped_db_url}")
    config.set_main_option("sqlalchemy.url", escaped_db_url)
else:
    print("[alembic/env.py] ⚠️ WARNING: SQLALCHEMY_DATABASE_URL from app.database is not set. Alembic might use a default from alembic.ini or fail.")

# Set the target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Force the correct URL for mysql-connector-python during Alembic runs
# This will override the one from alembic.ini for the engine creation below if it was different,
# and ensures it doesn't rely on os.getenv() which might be problematic.
# actual_db_url = "mysql+mysqlconnector://root:%%2B1826%%2BDark@localhost:3306/inp"  # Escaped % to %%
# config.set_main_option('sqlalchemy.url', actual_db_url) # REMOVED THIS HARDCODING

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url") # This will now pick up the URL we set above
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # The sqlalchemy.url is implicitly used here from the config object
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
