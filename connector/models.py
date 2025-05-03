from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# Lead models
class LeadBase(BaseModel):
    id: int
    name: str
    partner_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = Field(None, alias="email_from")
    phone: Optional[str] = None
    probability: Optional[float] = None
    expected_revenue: Optional[float] = None
    date_deadline: Optional[str] = None
    create_date: Optional[str] = None
    write_date: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None

    class Config:
        validate_by_name = True

class UserInfo(BaseModel):
    id: int
    name: str

class TeamInfo(BaseModel):
    id: int
    name: str

class StageInfo(BaseModel):
    id: int
    name: str

class LeadDetail(LeadBase):
    user_id: Optional[UserInfo] = None
    team_id: Optional[TeamInfo] = None
    stage_id: Optional[StageInfo] = None
    tags: Optional[List[str]] = None

class LeadListResponse(BaseModel):
    count: int
    limit: int
    offset: int
    data: List[LeadDetail]

# Meeting models
class MeetingBase(BaseModel):
    id: int
    name: str
    start_datetime: str = Field(..., alias="start")
    end_datetime: str = Field(..., alias="stop")
    duration: float
    location: Optional[str] = None
    description: Optional[str] = None

    class Config:
        validate_by_name = True

class OpportunityInfo(BaseModel):
    id: int
    name: str
    partner_name: Optional[str] = None
    stage_id: Optional[str] = None

class MeetingDetail(MeetingBase):
    user_id: Optional[UserInfo] = None
    opportunity_id: Optional[OpportunityInfo] = None

class MeetingListResponse(BaseModel):
    count: int
    limit: int
    offset: int
    data: List[MeetingDetail]

# Stage models
class Stage(BaseModel):
    id: int
    name: str
    sequence: int

class StageListResponse(BaseModel):
    data: List[Stage]

# Sales Team models
class TeamMember(BaseModel):
    id: int
    name: str
    login: str

class SalesTeam(BaseModel):
    id: int
    name: str
    user_id: Optional[Dict[str, Any]] = None
    members: Optional[List[TeamMember]] = None

class SalesTeamListResponse(BaseModel):
    data: List[SalesTeam]

# Dashboard models
class StageStats(BaseModel):
    id: int
    name: str
    sequence: int
    count: int = 0  # Default value for count
    expected_revenue: float = 0.0  # Default value for revenue

class TeamStats(BaseModel):
    id: int
    name: str
    count: int = 0  # Default value for count
    expected_revenue: float = 0.0  # Default value for revenue

class MonthlyMeeting(BaseModel):
    month: int
    month_name: str
    meeting_count: int = 0  # Default value for meeting count

class DashboardResponse(BaseModel):
    total_leads: int = 0  # Default value
    total_expected_revenue: float = 0.0  # Default value
    total_meetings: int = 0  # Default value
    stage_stats: List[StageStats]
    team_stats: List[TeamStats]
    monthly_meetings: List[MonthlyMeeting]