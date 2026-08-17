import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ApiSpec(Base):
    __tablename__ = "api_specs"

    spec_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    spec_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ApiSpec(id='{self.spec_id}', url='{self.spec_url}')>"