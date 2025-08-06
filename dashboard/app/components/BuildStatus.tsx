import { useEffect, useState } from "react";
import { getStaticMetadata } from "~/utils/api";

interface BuildStatusProps {
  className?: string;
  showDetails?: boolean;
}

interface Metadata {
  generated_at?: string;
  version?: string;
  mode?: string;
  total_teams?: number;
  total_members?: number;
  dashboard_data_count?: number;
  api_url?: string;
}

export function BuildStatus({ className = "", showDetails = false }: BuildStatusProps) {
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [isStatic, setIsStatic] = useState(false);

  useEffect(() => {
    getStaticMetadata()
      .then((data) => {
        setMetadata(data);
        setIsStatic(!!data?.generated_at);
      })
      .catch(() => {
        setIsStatic(false);
        setMetadata({ mode: "api", version: "live" });
      });
  }, []);

  if (!metadata) return null;

  const isStaticBuild = isStatic && metadata.generated_at;

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      {/* Status indicator */}
      <div className="flex items-center gap-1.5">
        <div
          className={`w-2 h-2 rounded-full ${
            isStaticBuild
              ? "bg-green-500 animate-pulse"
              : "bg-blue-500"
          }`}
        />
        <span className="text-xs font-medium text-gray-600">
          {isStaticBuild ? "Static" : "Live API"}
        </span>
      </div>

      {showDetails && metadata && (
        <div className="text-xs text-gray-500">
          {isStaticBuild ? (
            <span>
              Built: {new Date(metadata.generated_at!).toLocaleDateString()}
            </span>
          ) : (
            <span>Real-time data</span>
          )}
        </div>
      )}

      {/* Detailed info on hover */}
      {metadata && (
        <div className="relative group">
          <svg
            className="w-3 h-3 text-gray-400 cursor-help"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
              clipRule="evenodd"
            />
          </svg>

          {/* Tooltip */}
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-50 min-w-max">
            <div className="space-y-1">
              <div className="font-semibold border-b border-gray-700 pb-1">
                {isStaticBuild ? "Static Build Info" : "Live API Info"}
              </div>

              {isStaticBuild ? (
                <>
                  <div>Generated: {new Date(metadata.generated_at!).toLocaleString()}</div>
                  {metadata.total_teams && (
                    <div>Teams: {metadata.total_teams}</div>
                  )}
                  {metadata.total_members && (
                    <div>Members: {metadata.total_members}</div>
                  )}
                  {metadata.dashboard_data_count && (
                    <div>Dashboards: {metadata.dashboard_data_count}</div>
                  )}
                  <div className="text-green-400 text-xs italic">
                    Data is pre-generated and cached
                  </div>
                </>
              ) : (
                <>
                  <div>Mode: Real-time API</div>
                  {metadata.api_url && (
                    <div>API: {metadata.api_url}</div>
                  )}
                  <div className="text-blue-400 text-xs italic">
                    Data fetched from live server
                  </div>
                </>
              )}

              {metadata.version && (
                <div className="text-gray-400 text-xs pt-1 border-t border-gray-700">
                  v{metadata.version}
                </div>
              )}
            </div>

            {/* Arrow */}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45"></div>
          </div>
        </div>
      )}
    </div>
  );
}

export function BuildStatusCard() {
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [isStatic, setIsStatic] = useState(false);

  useEffect(() => {
    getStaticMetadata()
      .then((data) => {
        setMetadata(data);
        setIsStatic(!!data?.generated_at);
      })
      .catch(() => {
        setIsStatic(false);
        setMetadata({ mode: "api", version: "live" });
      });
  }, []);

  if (!metadata) return null;

  const isStaticBuild = isStatic && metadata.generated_at;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${
              isStaticBuild ? "bg-green-500" : "bg-blue-500"
            }`}
          />
          {isStaticBuild ? "Static Build" : "Live API"}
        </h3>

        {metadata.version && (
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            v{metadata.version}
          </span>
        )}
      </div>

      <div className="space-y-2 text-sm text-gray-600">
        {isStaticBuild ? (
          <>
            <div>
              <span className="font-medium">Generated:</span>{" "}
              {new Date(metadata.generated_at!).toLocaleString()}
            </div>

            {metadata.total_teams && (
              <div>
                <span className="font-medium">Teams:</span> {metadata.total_teams}
              </div>
            )}

            {metadata.total_members && (
              <div>
                <span className="font-medium">Members:</span> {metadata.total_members}
              </div>
            )}

            {metadata.dashboard_data_count && (
              <div>
                <span className="font-medium">Dashboards:</span> {metadata.dashboard_data_count}
              </div>
            )}

            <div className="text-green-600 text-xs italic mt-2 p-2 bg-green-50 rounded">
              ✓ All data is pre-generated and cached for optimal performance
            </div>
          </>
        ) : (
          <>
            <div>
              <span className="font-medium">Mode:</span> Real-time API
            </div>

            {metadata.api_url && (
              <div className="text-xs font-mono bg-gray-50 p-2 rounded">
                {metadata.api_url}
              </div>
            )}

            <div className="text-blue-600 text-xs italic mt-2 p-2 bg-blue-50 rounded">
              ⚡ Data is fetched live from the server
            </div>
          </>
        )}
      </div>
    </div>
  );
}
