from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TestCase(Base):
    __tablename__ = 'test_cases'

    id = Column(Integer, primary_key=True)
    api_spec_id = Column(String, nullable=False)
    request = Column(String, nullable=False)  # Store the request data (e.g., JSON string)
    expected_response = Column(String, nullable=False) # Store expected response data

    def __repr__(self):
        return f"<TestCase(id={self.id}, api_spec_id='{self.api_spec_id}')>"