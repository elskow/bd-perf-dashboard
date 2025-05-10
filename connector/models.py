from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# Base models
class BaseResponse(BaseModel):
    """Base response model with common fields"""
    message: Optional[str] = None
    error: Optional[str] = None

# Lead information
class LeadInfo(BaseModel):
    name: str  # Nama Leads
    industry: Optional[str] = None  # Industri
    stage: str  # Stage
    first_meeting_date: Optional[str] = None  # 1st Meeting Date
    warm_focus_date: Optional[str] = None  # Warm/Focus Date

# Meeting details
class MeetingDetail(BaseModel):
    name: str  # Nama Meeting
    date: str  # Tanggal

# Meeting statistics
class MeetingStats(BaseModel):
    first_meetings: int = 0  # 1ST
    second_meetings: int = 0  # 2ND
    third_meetings: int = 0  # 3RD
    more_meetings: int = 0  # 4+
    total_meetings: int = 0  # TOTAL

# Dashboard response
class DashboardResponse(BaseModel):
    salesperson_name: str
    leads: List[LeadInfo]
    meeting_stats: MeetingStats
    upcoming_meetings: List[MeetingDetail]

# User models
class UserInfo(BaseModel):
    id: int
    name: str
    login: str
    image_1920: Optional[str] = None

# Team models
class TeamInfo(BaseModel):
    id: int
    name: str

class TeamMember(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    user_id: Optional[Dict[str, Any]] = None
    members: List[UserInfo] = []

class SalesTeam(BaseModel):
    id: int
    name: str
    user_id: Optional[Dict[str, Any]] = None
    members: Optional[List[TeamMember]] = None

class SalesTeamListResponse(BaseModel):
    data: List[TeamMember]

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

# Monthly meeting stats
class MonthlyMeeting(BaseModel):
    month: int
    month_name: str
    meeting_count: int = 0

# Stage statistics
class StageStats(BaseModel):
    id: int
    name: str
    count: int = 0
    expected_revenue: float = 0.0

# Team stats
class TeamStats(BaseModel):
    id: int
    name: str
    count: int = 0
    expected_revenue: float = 0.0
    monthly_meetings: List[MonthlyMeeting]
    stage_stats: List[StageStats]