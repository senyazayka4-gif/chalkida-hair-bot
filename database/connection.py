from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import config

# Create Engine
# connect_args={"check_same_thread": False} is required for SQLite in multithreaded/async environments
engine = create_engine(
    config.DB_URL, 
    connect_args={"check_same_thread": False} if config.DB_URL.startswith("sqlite") else {}
)

# Create Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for models
Base = declarative_base()

@contextmanager
def get_db():
    """
    Context manager for database sessions.
    Automatically handles commits, rollbacks on exceptions, and closing sessions.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def init_db():
    """
    Initializes database tables if they do not exist.
    """
    Base.metadata.create_all(bind=engine)
    print("📂 Database tables initialized successfully.")
