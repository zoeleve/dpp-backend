# app/models/dpp.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.db.database_postgre import Base  # Assuming this is your base class

class DPP(Base):
    __tablename__ = "dpps"

    id = Column(Integer, primary_key=True, index=True)
    dpp_uuid = Column(String, unique=True, index=True, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    is_published = Column(Boolean, default=False, index=True)

    title = Column(String, nullable=False)
    product_identifier = Column(String, index=True, nullable=True)

    # JSONB for dynamic, queryable DPP data
    dpp_data = Column(JSONB, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
