interface StaticDataCache {
  salesTeams?: any;
  dashboards?: Record<string, any>;
  metadata?: any;
}

const staticCache: StaticDataCache = {};

// Check if we're in static mode (data files exist)
const isStaticMode = () => {
  // In production build, we'll have static data files
  return (
    (typeof window !== "undefined" && window.location.protocol === "file:") ||
    process.env.NODE_ENV === "production"
  );
};

// Fetch static data file
async function fetchStaticData(filename: string): Promise<any> {
  try {
    const response = await fetch(`/data/${filename}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch static data: ${filename}`);
    }
    return await response.json();
  } catch (error) {
    console.warn(`Static data not available: ${filename}`, error);
    return null;
  }
}

// Fallback to original API
async function fetchFromApi(endpoint: string): Promise<any> {
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:7001";
  const API_KEY = import.meta.env.VITE_API_KEY || "your-secure-api-key";

  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `API request failed: ${response.status} ${response.statusText}`
    );
  }

  return await response.json();
}

// Generic data fetcher that tries static first, then API
async function fetchData(
  staticFile: string,
  apiEndpoint: string
): Promise<any> {
  try {
    // Try static data first
    const staticData = await fetchStaticData(staticFile);
    if (staticData) {
      console.log(`Using static data: ${staticFile}`);
      return staticData;
    }
  } catch (error) {
    console.warn(
      `Static data unavailable, falling back to API for ${staticFile}`
    );
  }

  // Fallback to API
  console.log(`Using API: ${apiEndpoint}`);
  return await fetchFromApi(apiEndpoint);
}

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

export const fetchSalesTeams = async (): Promise<SalesTeamsResponse> => {
  if (staticCache.salesTeams) {
    return staticCache.salesTeams;
  }

  const data = await fetchData("sales-teams.json", "/api/salesteams");
  staticCache.salesTeams = data;
  return data;
};

export const fetchDashboardData = async (
  salespersonId: number
): Promise<DashboardData> => {
  // Check cache first
  if (staticCache.dashboards?.[salespersonId]) {
    return staticCache.dashboards[salespersonId];
  }

  let data;
  try {
    // Try individual static file first
    data = await fetchStaticData(`dashboard-${salespersonId}.json`);
    if (data) {
      console.log(`Using static data for salesperson ${salespersonId}`);
    } else {
      // Try combined static file
      if (!staticCache.dashboards) {
        const allDashboards = await fetchStaticData("all-dashboards.json");
        if (allDashboards) {
          staticCache.dashboards = allDashboards;
          data = allDashboards[salespersonId];
        }
      }
    }
  } catch (error) {
    console.warn(`Static dashboard data unavailable for ${salespersonId}`);
  }

  // Fallback to API if no static data
  if (!data) {
    console.log(`Using API for salesperson ${salespersonId}`);
    data = await fetchFromApi(`/api/dashboard?salesperson_id=${salespersonId}`);
  }

  // Cache the result
  if (!staticCache.dashboards) {
    staticCache.dashboards = {};
  }
  staticCache.dashboards[salespersonId] = data;

  return data;
};

export const checkApiHealth = async (): Promise<any> => {
  return await fetchData("health.json", "/api/health");
};

// Get metadata about the static build
export const getStaticMetadata = async (): Promise<any> => {
  try {
    return await fetchStaticData("metadata.json");
  } catch (error) {
    return {
      generated_at: null,
      version: "live-api",
      mode: "api",
    };
  }
};

// Preload all static data (useful for static builds)
export const preloadStaticData = async (): Promise<void> => {
  try {
    console.log("Preloading static data...");

    // Load metadata first
    const metadata = await getStaticMetadata();
    console.log("Static data metadata:", metadata);

    // Load sales teams
    await fetchSalesTeams();

    // Load all dashboard data
    if (!staticCache.dashboards) {
      const allDashboards = await fetchStaticData("all-dashboards.json");
      if (allDashboards) {
        staticCache.dashboards = allDashboards;
        console.log(
          `Preloaded dashboard data for ${
            Object.keys(allDashboards).length
          } salespeople`
        );
      }
    }

    console.log("Static data preloading complete");
  } catch (error) {
    console.warn("Failed to preload static data:", error);
  }
};

// Clear cache (useful for development)
export const clearCache = (): void => {
  staticCache.salesTeams = undefined;
  staticCache.dashboards = undefined;
  staticCache.metadata = undefined;
};

// Export cache for debugging
export const getCache = (): StaticDataCache => staticCache;
