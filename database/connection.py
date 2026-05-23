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
    
    # Auto-seed default monitored channels if empty
    from database.models import MonitoredChannel
    with get_db() as session:
        try:
            count = session.query(MonitoredChannel).count()
            if count == 0:
                print("🌱 Seeding default monitored channels...")
                for username in config.DEFAULT_MONITORED_CHANNELS:
                    new_ch = MonitoredChannel(
                        channel_username=username,
                        title=f"Локальный чат {username}",
                        is_active=True
                    )
                    session.add(new_ch)
                session.commit()
                print("✅ Default monitored channels seeded successfully.")
        except Exception as e:
            print(f"⚠️ Failed to seed default monitored channels: {e}")
