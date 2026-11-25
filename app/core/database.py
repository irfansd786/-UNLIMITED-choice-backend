import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings, CANONICAL_DB_PATH

logger = logging.getLogger("varshi_enterprises")

def _create_sqlite_engine(sqlite_url: str):
    if "sqlite:///" in sqlite_url:
        db_file = sqlite_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_file)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    return create_engine(sqlite_url, connect_args={"check_same_thread": False})

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Ensure proper driver for PostgreSQL in SQLAlchemy 2.0 (handles psycopg3 vs psycopg2)
if db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    try:
        import psycopg  # noqa: F401
    except ImportError:
        try:
            import psycopg2  # noqa: F401
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        except ImportError:
            pass

if "sqlite" in db_url:
    engine = _create_sqlite_engine(db_url)
else:
    try:
        pg_engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args={"connect_timeout": 3},
        )
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine = pg_engine
    except Exception as exc:
        logger.warning(
            "PostgreSQL unavailable (%s); falling back to SQLite at %s",
            exc,
            CANONICAL_DB_PATH,
        )
        engine = _create_sqlite_engine(f"sqlite:///{CANONICAL_DB_PATH}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
