import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

sys.path.append('/app')
config = context.config


database_url = os.environ.get('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

try:
    from backend.models import Base
    target_metadata = Base.metadata
except ImportError:
    try:
        from backend.database import Base
        target_metadata = Base.metadata
    except ImportError:
        try:
            from backend.models.user import Base
            target_metadata = Base.metadata
        except ImportError:
            print("Warning: Could not import Base from models. "
                  "target_metadata set to None")
            target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
