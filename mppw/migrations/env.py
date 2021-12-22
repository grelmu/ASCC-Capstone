import alembic
import mppw
import mppw.models

config = alembic.context.config

target_connection = None
try:

    if alembic.context.is_offline_mode():

        alembic.context.configure(
            url=mppw.storage.STORAGE_URL,
            target_metadata=mppw.models.registry.metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
    
    else:
        
        import mppw.storage
        storage_layer = mppw.storage.ModelStorageLayer.get_active()
        target_connection = storage_layer.engine.connect()

        mppw.logger.debug("Detected model tables: %s" % (mppw.models.registry.metadata.tables))

        alembic.context.configure(
            connection=target_connection,
            target_metadata=mppw.models.registry.metadata
        )

    with alembic.context.begin_transaction():
        alembic.context.run_migrations()

finally:
    if target_connection is not None:
        target_connection.close()
