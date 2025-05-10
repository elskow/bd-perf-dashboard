from pydantic import BaseModel
from typing import List, Optional, Dict, Any

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
class TeamMember(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    user_id: Optional[Dict[str, Any]] = None
    members: List[UserInfo] = []

class SalesTeamListResponse(BaseModel):
    data: List[TeamMember]