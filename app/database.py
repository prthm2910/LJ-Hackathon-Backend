import sqlalchemy
import config

def engine():
    """Creates a SQLAlchemy engine using a standard connection string."""
    db_uri = (
        f"postgresql+pg8000://{config.DB_USER}:{config.DB_PASS}@"
        f"{config.PUBLIC_IP}:{config.DB_PORT}/{config.DB_NAME}"
    )
    try:
        engine = sqlalchemy.create_engine(db_uri)
        # Test connection on creation
        with engine.connect() as connection:
            print("✅ Database connection successful.")
        return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise
