import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import your models here
from app.database import Base  # Ensure this path is correct
from app import models  # This will import all models

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Set the target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Force the correct URL for mysql-connector-python during Alembic runs
# This will override the one from alembic.ini for the engine creation below if it was different,
# and ensures it doesn't rely on os.getenv() which might be problematic.
# actual_db_url = "mysql+mysqlconnector://root:%%2B1826%%2BDark@localhost:3306/inp"  # Escaped % to %%
# config.set_main_option('sqlalchemy.url', actual_db_url) # REMOVED THIS HARDCODING

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
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
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
