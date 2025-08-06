#!/usr/bin/env node

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const API_URL = process.env.VITE_API_URL || "http://localhost:7001";
const API_KEY = process.env.VITE_API_KEY || "your-secure-api-key";
const OUTPUT_DIR = path.join(__dirname, "..", "public", "data");

// Check if we have fetch available
if (typeof fetch === "undefined") {
  console.log("fetch not available, importing node-fetch...");
  const { default: fetch } = await import("node-fetch");
  globalThis.fetch = fetch;
}

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// API request helper
async function apiRequest(endpoint) {
  try {
    console.log(`Fetching: ${API_URL}${endpoint}`);

    const response = await fetch(`${API_URL}${endpoint}`, {
      headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `API request failed: ${response.status} ${response.statusText} - ${errorText}`
      );
    }

    const data = await response.json();
    console.log(`✓ Successfully fetched ${endpoint}`);
    return data;
  } catch (error) {
    console.error(`✗ Error fetching ${endpoint}:`, error.message);
    throw error;
  }
}

// Save data to file
function saveData(filename, data) {
  const filepath = path.join(OUTPUT_DIR, filename);
  fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
  console.log(`✓ Saved data to ${filepath}`);
}

// Main data fetching function
async function fetchAllData() {
  console.log("🚀 Starting data fetch for static build...\n");

  try {
    // 1. Check API health
    console.log("1. Checking API health...");
    const health = await apiRequest("/api/health");
    saveData("health.json", health);

    if (!health.odoo_connected) {
      throw new Error("Odoo is not connected. Cannot proceed with data fetch.");
    }

    // 2. Fetch sales teams
    console.log("\n2. Fetching sales teams...");
    const salesTeams = await apiRequest("/api/salesteams");
    saveData("sales-teams.json", salesTeams);

    // 3. Fetch dashboard data for each team member
    console.log("\n3. Fetching dashboard data for each salesperson...");
    const dashboardData = {};

    for (const team of salesTeams.data) {
      for (const member of team.members) {
        try {
          console.log(
            `   Fetching data for ${member.name} (ID: ${member.id})...`
          );
          const memberData = await apiRequest(
            `/api/dashboard?salesperson_id=${member.id}`
          );
          dashboardData[member.id] = memberData;

          // Also save individual files for each salesperson
          saveData(`dashboard-${member.id}.json`, memberData);

          // Small delay to avoid overwhelming the API
          await new Promise((resolve) => setTimeout(resolve, 100));
        } catch (error) {
          console.error(
            `   ✗ Failed to fetch data for ${member.name}:`,
            error.message
          );
          // Continue with other members even if one fails
        }
      }
    }

    // Save combined dashboard data
    saveData("all-dashboards.json", dashboardData);

    // 4. Create metadata file
    const metadata = {
      generated_at: new Date().toISOString(),
      api_url: API_URL,
      total_teams: salesTeams.data.length,
      total_members: salesTeams.data.reduce(
        (sum, team) => sum + team.members.length,
        0
      ),
      dashboard_data_count: Object.keys(dashboardData).length,
      version: "1.0.0",
    };

    saveData("metadata.json", metadata);

    console.log("\n🎉 Data fetch completed successfully!");
    console.log(
      `📊 Generated data for ${metadata.total_members} team members across ${metadata.total_teams} teams`
    );
    console.log(`📁 Data saved to: ${OUTPUT_DIR}`);
  } catch (error) {
    console.error("\n❌ Data fetch failed:", error.message);
    process.exit(1);
  }
}

// Run the script
fetchAllData();
