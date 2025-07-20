from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Lead information
class LeadInfo(BaseModel):
    name: str  # Nama Leads
    industry: Optional[str] = None  # Industri
    stage: str  # Stage
    first_meeting_date: Optional[str] = None  # 1st Meeting Date
    warm_focus_date: Optional[str] = None  # Warm/Focus Date
    expected_revenue: Optional[float] = None  # Expected revenue
    probability: Optional[float] = None  # Win probability
    days_in_stage: Optional[int] = None  # Days in current stage (optional)
    meeting_count: Optional[int] = None  # Total meetings for this lead
    last_activity: Optional[str] = None  # Last activity date

# Meeting details
class MeetingDetail(BaseModel):
    name: str  # Nama Meeting
    date: str  # Tanggal
    type: Optional[str] = None  # Meeting type
    duration: Optional[float] = None  # Duration in hours

# Meeting statistics
class MeetingStats(BaseModel):
    first_meetings: int = 0  # 1ST
    second_meetings: int = 0  # 2ND
    third_meetings: int = 0  # 3RD
    more_meetings: int = 0  # 4+
    total_meetings: int = 0  # TOTAL

# Analytics data
class IndustryDistribution(BaseModel):
    industry: str
    count: int
    percentage: float

class StageDistribution(BaseModel):
    stage: str
    count: int
    total_value: float
    avg_days: float

class ConversionMetrics(BaseModel):
    stage: str
    count: int
    conversion_rate: float

class ActivityTimeline(BaseModel):
    date: str
    meetings: int
    calls: int
    emails: int

class KPIMetrics(BaseModel):
    total_leads: int
    qualified_leads: int
    conversion_rate: float
    avg_deal_size: float
    pipeline_value: float
    active_leads: int
    monthly_growth: float

class AnalyticsData(BaseModel):
    industry_distribution: List[IndustryDistribution]
    stage_distribution: List[StageDistribution]
    conversion_funnel: List[ConversionMetrics]
    activity_timeline: List[ActivityTimeline]
    kpi_metrics: KPIMetrics

# Dashboard response
class DashboardResponse(BaseModel):
    salesperson_name: str
    team_name: Optional[str] = None
    team_country: Optional[str] = None
    leads: List[LeadInfo]
    meeting_stats: MeetingStats
    upcoming_meetings: List[MeetingDetail]
    analytics: AnalyticsData

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
