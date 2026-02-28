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
# app.database raises ValueError if DATABASE_URL is not set, so we always have a valid URL here.
escaped_db_url = SQLALCHEMY_DATABASE_URL.replace('%', '%%')
config.set_main_option("sqlalchemy.url", escaped_db_url)

# Set the target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Note: The database URL is now loaded from app.database (which reads from .env)
# This ensures that the DATABASE_URL from environment variables is used for Alembic runs.
# The URL is set above from SQLALCHEMY_DATABASE_URL imported from app.database.
# Old hardcoded MySQL URL (removed):
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
