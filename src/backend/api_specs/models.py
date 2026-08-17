from typing import Optional

from pydantic import BaseModel

class APISpec(BaseModel):
    id: str
    spec_content: str