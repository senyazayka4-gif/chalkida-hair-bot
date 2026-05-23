from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from database.connection import Base

class User(Base):
    __tablename__ = "users"

    tg_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, nullable=True)
    fullname = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    appointments = relationship("Appointment", back_populates="user")

    @classmethod
    def get_or_create(cls, session, tg_id: int, username: str = None, fullname: str = None):
        """
        Retrieves user from database, or registers them if they do not exist.
        """
        user = session.query(cls).filter(cls.tg_id == tg_id).first()
        if not user:
            user = cls(
                tg_id=tg_id,
                username=username,
                fullname=fullname,
                is_admin=False
            )
            session.add(user)
            session.commit()
        return user


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.tg_id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    slot = Column(String, nullable=False)  # HH:MM
    status = Column(String, default="pending")  # pending, approved, completed, cancelled
    
    # Quiz Payload
    hair_length = Column(String, nullable=True)
    hair_type = Column(String, nullable=True)
    history_henna = Column(String, nullable=True)
    history_box_dye = Column(String, nullable=True)
    history_bleach = Column(String, nullable=True)
    desired_result = Column(Text, nullable=True)
    photo_path = Column(String, nullable=True)
    trichology_report = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="appointments")


class MonitoredChannel(Base):
    __tablename__ = "monitored_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_username = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
