import { useEffect, useState } from "react";
import { Link } from "react-router";
import type { Route } from "./+types/bd-list";
import { fetchSalesTeams, type SalesTeam} from "~/utils/api";
import { Loading } from "~/components/Loading";
import { Error } from "~/components/Error";
import { Avatar } from "~/components/Avatar";
import { getErrorMessage } from "~/utils/error";

const IndonesiaFlag = () => (
  <span className="text-lg" title="Indonesia">
    🇮🇩
  </span>
);

const SingaporeFlag = () => (
  <span className="text-lg" title="Singapore">
    🇸🇬
  </span>
);

const getCountryFlag = (teamName: string) => {
  if (teamName.includes("Indonesia")) {
    return <IndonesiaFlag />;
  } else if (teamName.includes("Singapore")) {
    return <SingaporeFlag />;
  }
  return (
    <div
      className="w-3 h-3 bg-gray-400 rounded-full"
      title="Unknown Team"
    ></div>
  );
};

export function meta({}: Route.MetaArgs) {
  return [
    { title: "BD Performance Dashboard" },
    {
      name: "description",
      content: "Business Development Performance Dashboard",
    },
  ];
}

export default function BDList() {
  const [teams, setTeams] = useState<SalesTeam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSalesTeams();
      setTeams(data.data);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading text="Loading BD teams..." />;
  }

  if (error) {
    return <Error message={error} onRetry={loadTeams} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 text-gray-900 py-8 sm:py-12 lg:py-16 overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-w-0">
        <div className="text-center mb-8 sm:mb-12 lg:mb-16 overflow-hidden">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-4 truncate">
            BD Weekly Report
          </h1>
          <div className="w-16 sm:w-20 lg:w-24 h-1 bg-gradient-to-r from-red-500 to-pink-600 mx-auto rounded-full"></div>
        </div>

        <div className="space-y-8 sm:space-y-12 max-w-6xl mx-auto min-w-0">
          {teams.map((team) => (
            <div key={team.id} className="space-y-4 sm:space-y-6">
              {/* Team Header */}
              <div className="flex items-center gap-3 justify-center">
                <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-sm border border-gray-200">
                  {getCountryFlag(team.name)}
                  <h2 className="text-lg font-bold text-gray-900">
                    {/* {team.name.replace("Sales ", "")} Team */}
                    {/* if indonesia, write as Jakarta team */}
                    {team.name.replace("Sales", "").includes("Indonesia")
                      ? "Jakarta"
                      : "Singapore"}{" "}
                    Team
                  </h2>
                  <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                    {team.members.length} BD
                    {team.members.length !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>

              {/* Team Members Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                {team.members.map((member) => (
                  <Link
                    key={member.id}
                    to={`/bd-dashboard/${member.id}`}
                    className="group block"
                  >
                    <div className="relative bg-white rounded-xl p-4 sm:p-5 shadow-sm hover:shadow-lg transition-all duration-300 border border-gray-200/50 hover:border-red-200 overflow-hidden min-w-0 transform">
                      {/* Subtle gradient overlay */}
                      <div className="absolute inset-0 bg-gradient-to-br from-red-50/30 to-pink-50/30 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>

                      {/* Content */}
                      <div className="relative space-y-3 min-w-0">
                        <div className="flex items-center gap-3 sm:gap-4 min-w-0">
                          <div className="relative">
                            <Avatar
                              name={member.name}
                              image={member.image_1920}
                              size="md"
                              className="flex-shrink-0 ring-2 ring-gray-100 group-hover:ring-red-200 transition-all duration-300"
                            />
                            {/* Country flag indicator */}
                            <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-white rounded-full border-2 border-gray-200 shadow-md flex items-center justify-center group-hover:border-red-200 transition-all duration-300 hover:scale-110">
                              {getCountryFlag(team.name)}
                            </div>
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="bg-gradient-to-r from-gray-900 to-gray-700 group-hover:from-red-600 group-hover:to-pink-600 text-white px-4 sm:px-6 py-2 sm:py-3 rounded-xl font-medium text-xs sm:text-sm text-center transition-all duration-300 shadow-sm min-w-0 overflow-hidden">
                              <span className="block truncate">
                                {member.name.toUpperCase()}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Enhanced corner accent with team color */}
                      <div className="absolute top-0 right-0 w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-bl from-red-100/40 to-transparent rounded-bl-full group-hover:from-red-200/60 transition-all duration-300"></div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
