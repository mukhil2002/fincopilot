from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

# Create the connection to PostgreSQL
engine = create_engine(DATABASE_URL)

# Factory for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy models later
Base = declarative_base()

def get_db():
    """
    Creates a database session for each request.
    Automatically closes it when the request is done.
    FastAPI calls this automatically on every protected endpoint.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection():
    """
    Tests if the database is reachable.
    Used by the /health endpoint.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False