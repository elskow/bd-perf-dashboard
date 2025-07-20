import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Area,
  AreaChart,
  Legend,
} from "recharts";

// Color palette
const COLORS = {
  primary: "#dc2626",
  secondary: "#ec4899",
  accent: "#f59e0b",
  success: "#10b981",
  warning: "#f59e0b",
  info: "#3b82f6",
  gray: "#6b7280",
};

const CHART_COLORS = [
  COLORS.primary,
  COLORS.secondary,
  COLORS.accent,
  COLORS.success,
  COLORS.info,
  "#8b5cf6",
  "#06b6d4",
  "#84cc16",
];

interface ChartCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  subtitle?: string;
}

export function ChartCard({
  title,
  children,
  className = "",
  subtitle,
}: ChartCardProps) {
  return (
    <div
      className={`bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6 overflow-hidden ${className}`}
    >
      <div className="mb-3 sm:mb-4 overflow-hidden">
        <h3 className="text-base sm:text-lg font-semibold text-gray-900 truncate">
          {title}
        </h3>
        {subtitle && (
          <p className="text-xs sm:text-sm text-gray-600 mt-1 truncate">
            {subtitle}
          </p>
        )}
      </div>
      <div className="overflow-hidden">{children}</div>
    </div>
  );
}

interface MeetingStatsChartProps {
  data: {
    first_meetings: number;
    second_meetings: number;
    third_meetings: number;
    more_meetings: number;
    total_meetings: number;
  };
}

export function MeetingStatsChart({ data }: MeetingStatsChartProps) {
  const chartData = [
    { name: "1st Meeting", value: data.first_meetings, color: COLORS.primary },
    {
      name: "2nd Meeting",
      value: data.second_meetings,
      color: COLORS.secondary,
    },
    { name: "3rd Meeting", value: data.third_meetings, color: COLORS.accent },
    { name: "4+ Meetings", value: data.more_meetings, color: COLORS.success },
  ];

  return (
    <ChartCard
      title="Meeting Distribution"
      subtitle="Number of leads by meeting count"
    >
      <div className="h-40 sm:h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: "#6b7280" }}
              axisLine={{ stroke: "#e5e7eb" }}
              interval={0}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#6b7280" }}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              }}
            />
            <Bar dataKey="value" fill="#dc2626" radius={[4, 4, 0, 0]}>
              {chartData.map((entry: { color: string }, index: number) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}

interface IndustryDistributionProps {
  data: Array<{ industry: string; count: number; percentage?: number }>;
}

const CenterLabel = ({ total, data }: { total: number; data: any[] }) => {
  return (
    <g>
      <text
        x="50%"
        y="42%"
        textAnchor="middle"
        dominantBaseline="middle"
        className="text-2xl font-bold fill-gray-900"
      >
        {total}
      </text>
    </g>
  );
};

const CustomLegend = ({ data }: { data: any[] }) => {
  if (!data || !Array.isArray(data) || data.length === 0) return null;

  const safeData = data.filter(
    (item) =>
      item &&
      typeof item === "object" &&
      typeof item.industry === "string" &&
      typeof item.count === "number" &&
      item.industry.trim().length > 0
  );

  if (safeData.length === 0) return null;

  return (
    <div className="flex flex-wrap justify-center gap-2 mt-4 px-2">
      {safeData.map((entry: any, index: number) => (
        <div
          key={index}
          className="group flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-gray-50 to-gray-100 hover:from-gray-100 hover:to-gray-200 rounded-lg border border-gray-200 hover:border-gray-300 transition-all duration-200 cursor-pointer shadow-sm hover:shadow-md"
        >
          <div
            className="w-3 h-3 rounded-full shadow-sm ring-2 ring-white group-hover:scale-110 transition-transform duration-200"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-xs font-semibold text-gray-700 truncate max-w-[70px] group-hover:text-gray-900 transition-colors">
            {entry.industry}
          </span>
          <span className="text-xs font-bold text-white bg-gray-600 group-hover:bg-gray-700 px-2 py-0.5 rounded-full transition-colors">
            {entry.count}
          </span>
        </div>
      ))}
    </div>
  );
};

export function IndustryDistributionChart({ data }: IndustryDistributionProps) {
  const enhancedColors = [
    "#dc2626", // Red
    "#ea580c", // Orange
    "#d97706", // Amber
    "#65a30d", // Lime
    "#059669", // Emerald
    "#0891b2", // Cyan
    "#2563eb", // Blue
    "#7c3aed", // Violet
    "#c026d3", // Fuchsia
    "#e11d48", // Rose
  ];

  const safeData =
    data && Array.isArray(data)
      ? data.filter((item) => {
          return (
            item &&
            typeof item === "object" &&
            typeof item.industry === "string" &&
            typeof item.count === "number" &&
            item.count >= 0 &&
            item.industry.trim().length > 0
          );
        })
      : [];
  const total = safeData.reduce((sum, item) => sum + item.count, 0);

  if (!safeData || safeData.length === 0 || total <= 0) {
    return (
      <ChartCard
        title="Industry Distribution"
        subtitle="Leads by industry type"
      >
        <div className="h-56 sm:h-64 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-gray-100 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-gray-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <p className="text-sm font-medium">No industry data available</p>
            <p className="text-xs text-gray-400 mt-1">
              Add some leads to see the distribution
            </p>
          </div>
        </div>
      </ChartCard>
    );
  }

  const chartData = safeData.map((item, index) => ({
    ...item,
    color: enhancedColors[index % enhancedColors.length],
    percentage: total > 0 ? (item.count / total) * 100 : 0,
  }));

  return (
    <ChartCard title="Industry Distribution" subtitle="Leads by industry type">
      <div className="h-56 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <defs>
              {chartData.map((entry, index) => (
                <React.Fragment key={index}>
                  <linearGradient
                    id={`gradient-${index}`}
                    x1="0"
                    y1="0"
                    x2="1"
                    y2="1"
                  >
                    <stop offset="0%" stopColor={entry.color} stopOpacity={1} />
                    <stop
                      offset="100%"
                      stopColor={entry.color}
                      stopOpacity={0.8}
                    />
                  </linearGradient>
                  <filter id={`shadow-${index}`}>
                    <feDropShadow
                      dx="2"
                      dy="2"
                      stdDeviation="3"
                      floodOpacity="0.3"
                    />
                  </filter>
                </React.Fragment>
              ))}
            </defs>
            <Pie
              data={chartData}
              cx="50%"
              cy="42%"
              outerRadius={75}
              innerRadius={30}
              paddingAngle={3}
              dataKey="count"
              labelLine={false}
              animationBegin={0}
              animationDuration={1200}
              stroke="white"
              strokeWidth={3}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={`url(#gradient-${index})`}
                  filter={`url(#shadow-${index})`}
                  style={{
                    filter: "drop-shadow(0px 2px 4px rgba(0,0,0,0.1))",
                    transition: "all 0.3s ease",
                  }}
                  className="hover:scale-105 cursor-pointer"
                />
              ))}
            </Pie>
            <CenterLabel total={total} data={chartData} />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  if (
                    !data ||
                    typeof data.industry !== "string" ||
                    typeof data.count !== "number"
                  ) {
                    return null;
                  }
                  return (
                    <div className="bg-white p-4 rounded-xl shadow-xl border border-gray-200 backdrop-blur-sm">
                      <div className="flex items-center gap-2 mb-2">
                        <div
                          className="w-4 h-4 rounded-full shadow-sm ring-2 ring-white"
                          style={{ backgroundColor: data.color }}
                        />
                        <span className="font-bold text-gray-900 text-sm">
                          {data.industry}
                        </span>
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between items-center">
                          <span className="text-gray-600">Leads:</span>
                          <span className="font-bold text-gray-900 bg-gray-100 px-2 py-0.5 rounded-md">
                            {data.count}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-gray-600">Share:</span>
                          <span className="font-bold text-red-700 bg-red-50 px-2 py-0.5 rounded-md">
                            {data.percentage.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <CustomLegend data={chartData} />
      </div>
    </ChartCard>
  );
}

interface StageDistributionProps {
  data: Array<{ stage: string; count: number; value?: number }>;
}

export function StageDistributionChart({ data }: StageDistributionProps) {
  const chartData = data.map((item, index) => ({
    ...item,
    color: CHART_COLORS[index % CHART_COLORS.length],
  }));

  return (
    <ChartCard
      title="Pipeline by Stage"
      subtitle="Leads distribution across sales stages"
    >
      <div className="h-40 sm:h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 10, bottom: 60 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis
              dataKey="stage"
              tick={{ fontSize: 9, fill: "#6b7280" }}
              axisLine={{ stroke: "#e5e7eb" }}
              angle={-45}
              textAnchor="end"
              height={60}
              interval={0}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#6b7280" }}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              }}
            />
            <Bar dataKey="count" fill={COLORS.primary} radius={[4, 4, 0, 0]}>
              {chartData.map((entry: { color: string }, index: number) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}

interface ConversionFunnelProps {
  data: Array<{ stage: string; count: number; conversionRate?: number }>;
}

export function ConversionFunnelChart({ data }: ConversionFunnelProps) {
  if (!data || data.length === 0) {
    return (
      <ChartCard
        title="Conversion Funnel"
        subtitle="Lead progression through sales stages"
      >
        <div className="text-center text-gray-500 py-8">
          No funnel data available
        </div>
      </ChartCard>
    );
  }

  const maxCount = Math.max(...data.map((item) => item.count));

  return (
    <ChartCard
      title="Conversion Funnel"
      subtitle="Lead progression through sales stages"
    >
      <div className="space-y-2 sm:space-y-3">
        {data.slice(0, 4).map((item, index) => {
          const percentage = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
          const width = Math.max(percentage, 5); // Minimum 5% width for visibility

          return (
            <div key={item.stage} className="relative overflow-hidden">
              <div className="flex items-center justify-between mb-1 gap-2">
                <span className="text-xs font-medium text-gray-700 truncate flex-1 min-w-0">
                  {item.stage}
                </span>
                <span className="text-xs font-semibold text-gray-900 flex-shrink-0">
                  {item.count}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-red-500 to-pink-500 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </ChartCard>
  );
}

interface ActivityTimelineProps {
  data: Array<{
    date: string;
    meetings: number;
    calls?: number;
    emails?: number;
  }>;
}

export function ActivityTimelineChart({ data }: ActivityTimelineProps) {
  return (
    <ChartCard title="Activity Timeline" subtitle="Meeting activity over time">
      <div className="h-40 sm:h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 10, left: 10, bottom: 5 }}
          >
            <defs>
              <linearGradient id="meetingGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={COLORS.primary}
                  stopOpacity={0.3}
                />
                <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: "#6b7280" }}
              axisLine={{ stroke: "#e5e7eb" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#6b7280" }}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              }}
            />
            <Area
              type="monotone"
              dataKey="meetings"
              stroke={COLORS.primary}
              fillOpacity={1}
              fill="url(#meetingGradient)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}

interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  color?: "primary" | "secondary" | "success" | "warning" | "info";
}

export function KPICard({
  title,
  value,
  change,
  changeLabel,
  icon,
  color = "primary",
}: KPICardProps) {
  const colorClasses = {
    primary: "from-red-500 to-pink-500",
    secondary: "from-pink-500 to-purple-500",
    success: "from-green-500 to-emerald-500",
    warning: "from-yellow-500 to-orange-500",
    info: "from-blue-500 to-indigo-500",
  };

  const changeColor =
    change && change > 0
      ? "text-green-600"
      : change && change < 0
      ? "text-red-600"
      : "text-gray-600";

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4 overflow-hidden">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0 overflow-hidden">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide truncate">
            {title}
          </p>
          <div className="text-lg sm:text-xl font-bold text-gray-900 mt-1 leading-tight overflow-hidden">
            <div className="truncate">
              {typeof value === "string" && value.length > 10 ? (
                <span className="text-sm sm:text-base block truncate">
                  {value}
                </span>
              ) : (
                <span className="block truncate">{value}</span>
              )}
            </div>
          </div>
          {change !== undefined && (
            <div className="flex items-center mt-1 overflow-hidden">
              {changeLabel && (
                <span className="text-xs text-gray-400 ml-1 truncate min-w-0">
                  {changeLabel}
                </span>
              )}
            </div>
          )}
        </div>
        {icon && (
          <div
            className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-gradient-to-br ${colorClasses[color]} flex items-center justify-center text-white flex-shrink-0 pr-1 pb-1`}
          >
            <div className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0">{icon}</div>
          </div>
        )}
      </div>
    </div>
  );
}

interface PerformanceComparisonProps {
  data: Array<{
    name: string;
    current: number;
    previous: number;
    target?: number;
  }>;
}

export function PerformanceComparisonChart({
  data,
}: PerformanceComparisonProps) {
  return (
    <ChartCard
      title="Performance Comparison"
      subtitle="Current vs previous period"
    >
      <div className="h-40 sm:h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: "#6b7280" }}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#6b7280" }}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              }}
            />
            <Legend />
            <Bar
              dataKey="current"
              fill={COLORS.primary}
              name="Current Period"
              radius={[2, 2, 0, 0]}
            />
            <Bar
              dataKey="previous"
              fill={COLORS.gray}
              name="Previous Period"
              radius={[2, 2, 0, 0]}
            />
            {data.some((item) => item.target) && (
              <Bar
                dataKey="target"
                fill={COLORS.success}
                name="Target"
                radius={[2, 2, 0, 0]}
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}
