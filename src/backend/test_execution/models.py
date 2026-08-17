from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class TestExecution(Base):
    __tablename__ = 'test_executions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)  # Assuming user ID from authentication module (MOD-001)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String) # e.g., "running", "completed", "failed"

    results = relationship("TestResult", backref="execution", cascade_delete=True)


class TestResult(Base):
    __tablename__ = 'test_results'

    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('test_executions.id'))
    test_case_id = Column(String) #ID of the test case executed (MOD-002)
    status = Column(String)  # "pass", "fail", "error"
    message = Column(String)
    execution_time = Column(DateTime, default=datetime.datetime.utcnow)