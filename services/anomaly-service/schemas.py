from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date

class ShiftData(BaseModel):
    id: Optional[str] = None
    shift_date: date
    platform: str
    hours_worked: float
    gross_earned: float
    platform_deductions: float
    net_received: float

class AnomalyRequest(BaseModel):
    worker_id: Optional[str] = None
    shifts: List[ShiftData]

class AnomalyDetail(BaseModel):
    type: str
    severity: str
    shift_id: Optional[str] = None
    shift_date: Optional[str] = None
    metric: Dict[str, Any]
    explanation: str

class AnomalyResponse(BaseModel):
    worker_id: Optional[str] = None
    total_shifts_analyzed: int
    anomalies_found: int
    anomalies: List[AnomalyDetail]
    summary: str

class RuleDetail(BaseModel):
    name: str
    description: str
    minimum_shifts_required: int
    severity: str
    what_it_catches: str

class RulesResponse(BaseModel):
    rules: List[RuleDetail]