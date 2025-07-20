import { useEffect, useState } from "react";
import type { Route } from "./+types/test-api";
import { checkApiHealth, fetchSalesTeams } from "~/utils/api";
import { PageLayout } from "~/components/PageLayout";
import { getErrorMessage } from "~/utils/error";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "API Test" },
    { name: "description", content: "Test API connectivity and responses" },
  ];
}

interface TestResult {
  test: string;
  status: "pending" | "success" | "error";
  message: string;
  data?: any;
}

export default function TestAPI() {
  const [tests, setTests] = useState<TestResult[]>([
    { test: "Health Check", status: "pending", message: "Testing..." },
    { test: "Sales Teams", status: "pending", message: "Testing..." },
  ]);

  useEffect(() => {
    runTests();
  }, []);

  const updateTest = (index: number, result: Partial<TestResult>) => {
    setTests((prev) =>
      prev.map((test, i) => (i === index ? { ...test, ...result } : test))
    );
  };

  const runTests = async () => {
    try {
      const healthData = await checkApiHealth();
      updateTest(0, {
        status: "success",
        message: "API is healthy",
        data: healthData,
      });
    } catch (error: unknown) {
      updateTest(0, {
        status: "error",
        message: getErrorMessage(error),
      });
    }

    try {
      const teamsData = await fetchSalesTeams();
      updateTest(1, {
        status: "success",
        message: `Found ${teamsData.data.length} teams`,
        data: teamsData,
      });
    } catch (error: unknown) {
      updateTest(1, {
        status: "error",
        message: getErrorMessage(error),
      });
    }
  };

  const getStatusIcon = (status: TestResult["status"]) => {
    switch (status) {
      case "pending":
        return (
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
        );
      case "success":
        return (
          <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
            <svg
              className="w-3 h-3 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        );
      case "error":
        return (
          <div className="w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
            <svg
              className="w-3 h-3 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        );
    }
  };

  return (
    <PageLayout
      title="API Test Page"
      showBackButton={true}
      backButtonText="← Back to BD Dashboard"
      backButtonHref="/bd-list"
      className="max-w-4xl"
    >
      <div className="flex justify-end mb-8">
        <button
          onClick={runTests}
          className="bg-gradient-to-r from-red-600 to-pink-600 text-white px-4 py-2 rounded-lg hover:from-red-700 hover:to-pink-700 transition-all duration-300 shadow-sm"
        >
          Run Tests Again
        </button>
      </div>

      <div className="space-y-6">
        {tests.map((test, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-6 text-gray-900"
          >
            <div className="flex items-center gap-3 mb-4">
              {getStatusIcon(test.status)}
              <h2 className="text-xl font-semibold text-gray-900">
                {test.test}
              </h2>
            </div>

            <p
              className={`mb-4 ${
                test.status === "error"
                  ? "text-red-600"
                  : test.status === "success"
                  ? "text-green-600"
                  : "text-gray-600"
              }`}
            >
              {test.message}
            </p>

            {test.data && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                  View Raw Response
                </summary>
                <pre className="mt-2 p-4 bg-gray-100 rounded text-xs overflow-x-auto">
                  {JSON.stringify(test.data, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ))}
      </div>

      <div className="mt-8 p-4 bg-gray-50 rounded-lg text-gray-900">
        <h3 className="font-semibold text-gray-900 mb-2">Configuration</h3>
        <div className="text-sm text-gray-600 space-y-1">
          <div>
            API URL: {import.meta.env.VITE_API_URL || "http://localhost:7001"}
          </div>
          <div>
            API Key:{" "}
            {import.meta.env.VITE_API_KEY ? "Configured" : "Using default"}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
