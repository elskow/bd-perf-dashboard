// Import the static data service
import * as StaticApi from "./staticApi";

// Re-export types from static API for backward compatibility
export type {
  TeamMember,
  SalesTeam,
  SalesTeamsResponse,
  LeadInfo,
  MeetingStats,
  MeetingDetail,
  IndustryDistribution,
  StageDistribution,
  ConversionMetrics,
  ActivityTimeline,
  KPIMetrics,
  AnalyticsData,
  DashboardData,
} from "./staticApi";

// Use static API methods with fallback to original API
export const fetchSalesTeams = StaticApi.fetchSalesTeams;
export const fetchDashboardData = StaticApi.fetchDashboardData;
export const checkApiHealth = StaticApi.checkApiHealth;

// Additional utilities from static API
export const getStaticMetadata = StaticApi.getStaticMetadata;
export const preloadStaticData = StaticApi.preloadStaticData;
export const clearCache = StaticApi.clearCache;
