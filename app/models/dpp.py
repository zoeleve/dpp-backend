from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from app.db.database_postgre import Base

class DPP(Base):
    __tablename__ = "dpp"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, unique=True, nullable=False)
    manufacturer = Column(String, nullable=False)
    model = Column(String, nullable=False)
    category = Column(String, nullable=True)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
