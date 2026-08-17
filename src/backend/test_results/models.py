from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TestExecution(Base):
    __tablename__ = 'test_executions'

    id = Column(Integer, primary_key=True)
    test_case_id = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)


class TestResultStatus(Enum):
    PASS = 'pass'
    FAIL = 'fail'

class TestResult(Base):
    __tablename__ = 'test_results'

    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, nullable=False)
    status = Column(Enum(TestResultStatus), nullable=False)
    response = Column(String, nullable=True)  # Store response as string (JSON serializable)
    test_case_id = Column(String, nullable=False) # Add test case ID for easier filtering/queries