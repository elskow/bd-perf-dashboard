const API_URL = import.meta.env.VITE_API_URL || "http://192.168.0.164:7001";
const API_KEY = import.meta.env.VITE_API_KEY || "your-secure-api-key";

export interface TeamMember {
  id: number;
  name: string;
  login: string;
  image_1920?: string;
}

export interface SalesTeam {
  id: number;
  name: string;
  user_id?: { id: number; name: string };
  members: TeamMember[];
}

export interface SalesTeamsResponse {
  data: SalesTeam[];
}

export interface LeadInfo {
  name: string;
  industry: string;
  stage: string;
  first_meeting_date?: string;
  warm_focus_date?: string;
  expected_revenue?: number;
  probability?: number;
  days_in_stage?: number;
  meeting_count?: number;
  last_activity?: string;
}

export interface MeetingStats {
  first_meetings: number;
  second_meetings: number;
  third_meetings: number;
  more_meetings: number;
  total_meetings: number;
}

export interface MeetingDetail {
  name: string;
  date: string;
  type?: string;
  duration?: number;
}

export interface IndustryDistribution {
  industry: string;
  count: number;
  percentage: number;
}

export interface StageDistribution {
  stage: string;
  count: number;
  total_value: number;
  avg_days: number;
}

export interface ConversionMetrics {
  stage: string;
  count: number;
  conversion_rate: number;
}

export interface ActivityTimeline {
  date: string;
  meetings: number;
  calls: number;
  emails: number;
}

export interface KPIMetrics {
  total_leads: number;
  qualified_leads: number;
  conversion_rate: number;
  avg_deal_size: number;
  pipeline_value: number;
  active_leads: number;
  monthly_growth: number;
}

export interface AnalyticsData {
  industry_distribution: IndustryDistribution[];
  stage_distribution: StageDistribution[];
  conversion_funnel: ConversionMetrics[];
  activity_timeline: ActivityTimeline[];
  kpi_metrics: KPIMetrics;
}

export interface DashboardData {
  salesperson_name: string;
  team_name?: string;
  team_country?: string;
  leads: LeadInfo[];
  meeting_stats: MeetingStats;
  upcoming_meetings: MeetingDetail[];
  analytics: AnalyticsData;
}

const apiRequest = async (endpoint: string): Promise<any> => {
  try {
    console.log(`Making API request to: ${API_URL}${endpoint}`);

    const response = await fetch(`${API_URL}${endpoint}`, {
      headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        `API request failed: ${response.status} ${response.statusText}`,
        errorText
      );
      throw new Error(
        `API request failed: ${response.status} ${response.statusText}`
      );
    }

    const data = await response.json();
    console.log(`API response received for ${endpoint}:`, data);
    return data;
  } catch (error) {
    console.error(`Error making API request to ${endpoint}:`, error);
    if (
      error instanceof TypeError &&
      error.message.includes("Failed to fetch")
    ) {
      throw new Error(
        "Unable to connect to the API server. Please check if the backend is running."
      );
    }
    throw error;
  }
};

export const fetchSalesTeams = async (): Promise<SalesTeamsResponse> => {
  return apiRequest("/api/salesteams");
};

export const fetchDashboardData = async (
  salespersonId: number
): Promise<DashboardData> => {
  return apiRequest(`/api/dashboard?salesperson_id=${salespersonId}`);
};

export const checkApiHealth = async (): Promise<any> => {
  return apiRequest("/api/health");
};
