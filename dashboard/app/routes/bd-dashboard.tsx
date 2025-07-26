import { useEffect, useState, useMemo } from "react";
import { useParams } from "react-router";
import type { Route } from "./+types/bd-dashboard";
import { fetchDashboardData, type DashboardData } from "~/utils/api";
import { Loading } from "~/components/Loading";
import { Error } from "~/components/Error";
import { Avatar } from "~/components/Avatar";
import { PageLayout } from "~/components/PageLayout";
import { DataTable } from "~/components/DataTable";
import {
  MeetingStatsChart,
  IndustryDistributionChart,
  ConversionFunnelChart,
  KPICard,
} from "~/components/Charts";
import { getErrorMessage } from "~/utils/error";
import {
  transformLeadsForTable,
  exportLeadsToCSV,
  formatCurrency,
  formatPercentage,
  getStageColor,
  getIndustryColor,
  sortByDate,
} from "~/utils/dataUtils";
import { type ColumnDef } from "@tanstack/react-table";
import { Users, DollarSign, Calendar, Target, Percent } from "lucide-react";

const IndonesiaFlag = () => (
  <span className="text-sm" title="Indonesia">
    🇮🇩
  </span>
);

const SingaporeFlag = () => (
  <span className="text-sm" title="Singapore">
    🇸🇬
  </span>
);

const getTeamInfo = (teamCountry?: string, teamName?: string) => {
  if (teamCountry === "Indonesia" || teamName?.includes("Indonesia")) {
    return {
      flag: <IndonesiaFlag />,
      teamText: "Jakarta Team",
      flagBg: "bg-red-50",
      textColor: "text-red-700",
    };
  } else if (teamCountry === "Singapore" || teamName?.includes("Singapore")) {
    return {
      flag: <SingaporeFlag />,
      teamText: "Singapore Team",
      flagBg: "bg-red-50",
      textColor: "text-red-700",
    };
  }

  return {
    flag: (
      <div
        className="w-4 h-4 bg-gray-300 rounded-full flex items-center justify-center"
        title="Unknown Team"
      >
        <span className="text-xs text-gray-500">?</span>
      </div>
    ),
    teamText: "Unknown Team",
    flagBg: "bg-gray-50",
    textColor: "text-gray-600",
  };
};

export function meta({}: Route.MetaArgs) {
  return [
    { title: "BD Weekly Report" },
    {
      name: "description",
      content: "Business Development Weekly Report Dashboard",
    },
  ];
}

export default function BDDashboard() {
  const { id } = useParams();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadDashboardData(parseInt(id));
    }
  }, [id]);

  const loadDashboardData = async (salespersonId: number) => {
    setLoading(true);
    setError(null);
    try {
      const dashboardData = await fetchDashboardData(salespersonId);
      setData(dashboardData);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFilterClick = (column: string, value: string) => {
    console.log(`Filtering ${column} by ${value}`);
  };

  const transformedLeads = useMemo(() => {
    if (!data?.leads) return [];
    return transformLeadsForTable(data.leads);
  }, [data?.leads]);

  const leadsColumns = useMemo<ColumnDef<any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Lead",
        cell: ({ row }) => (
          <div className="min-w-0 max-w-[160px] sm:max-w-[180px]">
            <div
              className="font-medium text-gray-900 text-xs sm:text-sm leading-snug truncate cursor-default"
              title={row.getValue("name")}
            >
              {row.getValue("name")}
            </div>
            {/* Mobile-only additional info */}
            <div className="block sm:hidden text-xs text-gray-600 mt-1.5 space-y-1.5">
              <div className="flex items-center gap-1.5">
                <span
                  className={`inline-flex px-1.5 py-0.5 text-xs italic font-normal rounded-full ${getIndustryColor(
                    row.original.industry
                  )}`}
                >
                  {row.original.industry.slice(0, 3)}
                </span>
                <span
                  className={`inline-flex px-1.5 py-0.5 text-xs italic font-normal rounded-full ${getStageColor(
                    row.original.stage
                  )}`}
                >
                  {row.original.stage.slice(0, 3)}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-gray-800">
                  {formatCurrency(row.original.expected_revenue)}
                </span>
                <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-normal tracking-wide">
                  {row.original.meeting_count || 0}m
                </span>
              </div>
            </div>
          </div>
        ),
      },
      {
        accessorKey: "industry",
        header: "Industry",
        cell: ({ row }) => {
          const industry = row.getValue("industry");
          return (
            <div className="flex justify-start">
              <span
                className={`inline-flex px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-normal italic rounded-full ${getIndustryColor(
                  industry
                )} tracking-wide`}
              >
                {industry}
              </span>
            </div>
          );
        },
        filterFn: "multiValue",
        meta: {
          className: "hidden sm:table-cell",
        },
      },
      {
        accessorKey: "stage",
        header: "Stage",
        cell: ({ row }) => {
          const stage = row.getValue("stage");
          return (
            <div className="flex justify-start">
              <span
                className={`inline-flex px-1.5 sm:px-2 py-0.5 sm:py-1 text-xs font-normal uppercase tracking-wider rounded-full ${getStageColor(
                  stage
                )}`}
              >
                {stage}
              </span>
            </div>
          );
        },
        filterFn: "multiValue",
        meta: {
          className: "hidden sm:table-cell",
        },
      },
      {
        accessorKey: "expected_revenue",
        header: "Revenue",
        cell: ({ row }) => (
          <div className="text-right">
            <span className="font-medium text-gray-900 text-xs sm:text-sm tabular-nums">
              {formatCurrency(row.getValue("expected_revenue"))}
            </span>
          </div>
        ),
        meta: {
          className: "hidden lg:table-cell",
        },
      },
      {
        accessorKey: "probability",
        header: "%",
        cell: ({ row }) => (
          <div className="text-right">
            <span className="font-normal text-gray-600 text-xs sm:text-sm tabular-nums italic">
              {formatPercentage(row.getValue("probability"))}
            </span>
          </div>
        ),
        meta: {
          className: "hidden lg:table-cell",
        },
      },
      {
        id: "meeting_count",
        header: "Meetings",
        accessorFn: (row) => row.meeting_count || 0,
        cell: ({ getValue }) => {
          const meetingCount = getValue();
          return (
            <div className="flex justify-center">
              <span className="inline-flex items-center justify-center w-5 h-5 sm:w-6 sm:h-6 text-xs font-black text-white bg-red-500 rounded-full tabular-nums">
                {meetingCount}
              </span>
            </div>
          );
        },
        sortingFn: (rowA, rowB, columnId) => {
          const a = Number(rowA.getValue(columnId)) || 0;
          const b = Number(rowB.getValue(columnId)) || 0;
          return a - b;
        },
        meta: {
          className: "hidden sm:table-cell",
        },
      },

      {
        accessorKey: "first_meeting_date",
        header: "1st Meet",
        cell: ({ row }) => (
          <div className="text-center">
            <span className="text-xs font-mono text-gray-600 bg-gray-50 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded tracking-tight">
              {row.getValue("first_meeting_date") || "-"}
            </span>
          </div>
        ),
        sortingFn: "customDateSort",
        meta: {
          className: "hidden lg:table-cell",
        },
      },
      {
        accessorKey: "warm_focus_date",
        header: "Warm",
        cell: ({ row }) => (
          <div className="text-center">
            <span className="text-xs font-mono text-gray-600 bg-gray-50 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded tracking-tight">
              {row.getValue("warm_focus_date") || "-"}
            </span>
          </div>
        ),
        sortingFn: "customDateSort",
        meta: {
          className: "hidden lg:table-cell",
        },
      },
    ],
    []
  );

  if (loading) {
    return <Loading text="Loading dashboard..." />;
  }

  if (error || !data) {
    return (
      <Error
        message={error || "No data available"}
        onRetry={() => id && loadDashboardData(parseInt(id))}
      />
    );
  }

  return (
    <PageLayout
      showBackButton={true}
      backButtonText="← Back to BD List"
      backButtonHref="/bd-list"
      className="container-safe"
    >
      {/* Header with ID Card */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 sm:mb-8 gap-4 sm:gap-6">
        <div className="flex-1 min-w-0">
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 truncate">
            Overview Report
          </h1>
          <p className="text-sm text-gray-600 mt-1 truncate">
            Business Development Performance Dashboard
          </p>
        </div>

        {/* ID Card Style Profile */}
        <div className="id-card rounded-2xl shadow-lg border border-gray-200/60 p-4 sm:p-5 w-full sm:w-auto sm:min-w-[280px] lg:min-w-[320px] sm:max-w-[400px] overflow-hidden group transition-all duration-500 transform">
          {/* Card Background Pattern */}
          <div className="absolute inset-0 bg-gradient-to-r from-red-500/5 to-pink-500/5 opacity-100 transition-opacity duration-500"></div>

          {/* Subtle geometric pattern */}
          <div className="absolute top-0 right-0 w-32 h-32 id-card-pattern"></div>

          {/* Card Content */}
          <div className="relative flex items-center gap-3 sm:gap-4 min-w-0 overflow-hidden">
            <div className="relative">
              <div className="id-card-avatar-ring">
                <Avatar
                  name={data.salesperson_name}
                  size="md"
                  className="ring-2 ring-red-50 transition-all duration-300 flex-shrink-0"
                />
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <div className="text-sm sm:text-base font-bold text-gray-900 truncate transition-colors duration-300">
                {data.salesperson_name}
              </div>
              <div className="text-xs text-gray-500 truncate font-medium">
                Business Development
              </div>
              <div className="flex items-center justify-between mt-1.5">
                <div className="flex items-center gap-2">
                  {getTeamInfo(data.team_country, data.team_name).flag}
                  <span
                    className={`text-xs font-semibold ${
                      getTeamInfo(data.team_country, data.team_name).textColor
                    }`}
                  >
                    {getTeamInfo(data.team_country, data.team_name).teamText}
                  </span>
                </div>
                <div className="px-2 py-0.5 bg-red-50 text-red-600 text-xs font-medium rounded-full">
                  BD
                </div>
              </div>
            </div>
          </div>

          {/* Enhanced card corner accents */}
          <div className="absolute top-0 right-0 w-12 h-12 bg-gradient-to-bl to-transparent rounded-bl-2xl from-red-200/60 via-pink-200/40 transition-all duration-500"></div>
          <div className="absolute bottom-0 left-0 w-8 h-8 bg-gradient-to-tr from-gray-100/60 to-transparent rounded-tr-2xl"></div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 mb-6 lg:mb-8 grid-safe">
        <KPICard
          title="Total Leads"
          value={data.analytics.kpi_metrics.total_leads}
          icon={<Users className="w-6 h-6 mx-auto" />}
          color="primary"
        />
        <KPICard
          title="Pipeline Value"
          value={formatCurrency(data.analytics.kpi_metrics.pipeline_value)}
          icon={<DollarSign className="w-6 h-6" />}
          color="success"
        />
        <KPICard
          title="Conversion Rate"
          value={formatPercentage(data.analytics.kpi_metrics.conversion_rate)}
          icon={<Percent className="w-6 h-6" />}
          color="info"
        />
        <KPICard
          title="Active Leads"
          value={data.analytics.kpi_metrics.active_leads}
          icon={<Target className="w-6 h-6" />}
          color="warning"
        />
      </div>

      {/* Charts Section - Reduced to 2 most important charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 lg:gap-8 mb-6 lg:mb-8 grid-safe">
        <MeetingStatsChart data={data.meeting_stats} />
        <ConversionFunnelChart data={data.analytics.conversion_funnel} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8 grid-safe">
        {/* Enhanced Leads Table */}
        <div className="lg:col-span-2 order-2 lg:order-1 container-safe">
          <DataTable
            data={transformedLeads}
            columns={leadsColumns}
            title="Leads Overview"
            searchable={true}
            searchPlaceholder="Search leads..."
            exportable={true}
            onExport={() => exportLeadsToCSV(data.leads)}
            pageSize={8}
            compact={true}
            showPageSizeSelector={true}
            pageSizeOptions={[5, 8, 15, 25, 50]}
            initialSorting={[{ id: "first_meeting_date", desc: true }]}
            filterable={true}
            filterableColumns={["industry", "stage"]}
            onFilterClick={handleFilterClick}
          />
        </div>

        {/* Right Column - Upcoming Meetings */}
        <div className="space-y-4 lg:space-y-6 order-1 lg:order-2 container-safe">
          {/* Upcoming Meetings */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 card-safe">
            <div className="p-3 border-b border-gray-200 bg-gray-50">
              <h3 className="text-base font-semibold text-gray-900">
                Upcoming Meetings
              </h3>
            </div>
            <div className="divide-y divide-gray-200">
              {data.upcoming_meetings.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  No upcoming meetings
                </div>
              ) : (
                data.upcoming_meetings.slice(0, 4).map((meeting, index) => (
                  <div
                    key={index}
                    className="p-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-2 flex-safe">
                      <div className="w-1.5 h-1.5 bg-red-500 rounded-full flex-shrink-0"></div>
                      <div className="flex-1 container-safe">
                        <p className="text-sm font-medium text-gray-900 truncate-1-line">
                          {meeting.name}
                        </p>
                        <p className="text-xs text-gray-500 truncate-1-line">
                          {meeting.date || "-"}
                        </p>
                      </div>
                      <Calendar className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Additional Charts - Minimized */}
          <div className="space-y-3">
            <details className="lg:hidden">
              <summary className="cursor-pointer text-xs font-medium text-gray-600 bg-gray-50 p-2 rounded-md">
                More Analytics
              </summary>
              <div className="mt-2 space-y-2">
                <IndustryDistributionChart
                  data={data.analytics.industry_distribution}
                />
              </div>
            </details>
            <div className="hidden lg:block">
              <IndustryDistributionChart
                data={data.analytics.industry_distribution}
              />
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
