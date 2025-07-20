import { format } from "date-fns";

export const formatCurrency = (
  amount: number | null | undefined,
  currency = "IDR"
): string => {
  if (amount === null || amount === undefined) return "-";

  const absAmount = Math.abs(amount);
  const currencySymbol =
    currency === "IDR" ? "Rp" : currency === "USD" ? "$" : "";

  if (absAmount >= 1000000000) {
    return `${currencySymbol}${(amount / 1000000000).toFixed(1)}B`;
  } else if (absAmount >= 1000000) {
    return `${currencySymbol}${(amount / 1000000).toFixed(1)}M`;
  } else if (absAmount >= 1000) {
    return `${currencySymbol}${(amount / 1000).toFixed(1)}K`;
  } else {
    return `${currencySymbol}${amount.toFixed(0)}`;
  }
};

export const formatPercentage = (num: number | null | undefined): string => {
  if (num === null || num === undefined) return "-";

  return `${num.toFixed(1)}%`;
};

export const getStageColor = (stage: string): string => {
  const stageColors: Record<string, string> = {
    NEW: "bg-gray-100 text-gray-800",
    QUALIFIED: "bg-blue-100 text-blue-800",
    PROPOSITION: "bg-yellow-100 text-yellow-800",
    NEGOTIATION: "bg-orange-100 text-orange-800",
    WON: "bg-green-100 text-green-800",
    LOST: "bg-red-100 text-red-800",
    WARM: "bg-pink-100 text-pink-800",
    FOCUS: "bg-purple-100 text-purple-800",
    CONTRACT: "bg-indigo-100 text-indigo-800",
  };

  return stageColors[stage.toUpperCase()] || "bg-gray-100 text-gray-800";
};

export const getIndustryColor = (industry: string): string => {
  const industryColors: Record<string, string> = {
    TECHNOLOGY: "bg-blue-100 text-blue-800",
    FINANCE: "bg-green-100 text-green-800",
    HEALTHCARE: "bg-red-100 text-red-800",
    EDUCATION: "bg-purple-100 text-purple-800",
    RETAIL: "bg-orange-100 text-orange-800",
    MANUFACTURING: "bg-gray-100 text-gray-800",
    UNKNOWN: "bg-gray-100 text-gray-600",
  };

  return industryColors[industry.toUpperCase()] || "bg-gray-100 text-gray-600";
};

export const transformLeadsForTable = (leads: any[]) => {
  return leads.map((lead) => ({
    ...lead,
    formattedRevenue: formatCurrency(lead.expected_revenue),
    formattedProbability: formatPercentage(lead.probability),
    stageColor: getStageColor(lead.stage),
    industryColor: getIndustryColor(lead.industry),
    first_meeting_date:
      lead.first_meeting_date && lead.first_meeting_date !== "-"
        ? lead.first_meeting_date
        : "-",
    warm_focus_date:
      lead.warm_focus_date && lead.warm_focus_date !== "-"
        ? lead.warm_focus_date
        : "-",
    last_activity:
      lead.last_activity && lead.last_activity !== "-"
        ? lead.last_activity
        : "-",
  }));
};

export const exportToCSV = (data: any[], filename: string) => {
  if (!data || data.length === 0) return;

  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(","),
    ...data.map((row) =>
      headers
        .map((header) => {
          const value = row[header];
          if (
            typeof value === "string" &&
            (value.includes(",") || value.includes('"'))
          ) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return value;
        })
        .join(",")
    ),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");

  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `${filename}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
};

export const exportLeadsToCSV = (leads: any[]) => {
  const exportData = leads.map((lead) => ({
    "Lead Name": lead.name,
    Industry: lead.industry,
    Stage: lead.stage,
    "Expected Revenue": formatCurrency(lead.expected_revenue),
    Probability: lead.probability || 0,
    "Days in Stage": lead.days_in_stage || 0,
    "Meeting Count": lead.meeting_count || 0,
    "First Meeting Date": lead.first_meeting_date || "-",
    "Warm/Focus Date": lead.warm_focus_date || "-",
    "Last Activity": lead.last_activity || "-",
  }));

  exportToCSV(exportData, `leads-export-${format(new Date(), "yyyy-MM-dd")}`);
};

export const sortByDate = (a: string, b: string, desc = false) => {
  if (a === "-" && b === "-") return 0;
  if (a === "-") return 1;
  if (b === "-") return -1;

  // Parse dates in "DD MMM" format (e.g., "15 MAR", "20 DEC")
  const parseShortDate = (dateStr: string): Date => {
    if (!dateStr || dateStr === "-") return new Date(0);

    try {
      const [day, month] = dateStr.split(" ");
      const monthMap: Record<string, number> = {
        JAN: 0,
        FEB: 1,
        MAR: 2,
        APR: 3,
        MAY: 4,
        JUN: 5,
        JUL: 6,
        AUG: 7,
        SEP: 8,
        OCT: 9,
        NOV: 10,
        DEC: 11,
      };

      const monthIndex = monthMap[month?.toUpperCase()];
      if (monthIndex !== undefined && day) {
        const currentYear = new Date().getFullYear();
        return new Date(currentYear, monthIndex, parseInt(day));
      }
    } catch (error) {
      return new Date(dateStr);
    }

    return new Date(dateStr);
  };

  const dateA = parseShortDate(a);
  const dateB = parseShortDate(b);

  if (isNaN(dateA.getTime())) return 1;
  if (isNaN(dateB.getTime())) return -1;

  return desc
    ? dateB.getTime() - dateA.getTime()
    : dateA.getTime() - dateB.getTime();
};
