"""Alembic environment. The URL comes from the same settings the application reads."""

from alembic import context

from app.db import Base, build_url, get_engine
import core.models  # noqa: F401  (registers every table on Base.metadata)

config = context.config
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=build_url(), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={'paramstyle': 'named'})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
