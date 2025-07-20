import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("/bd-list", "routes/bd-list.tsx"),
  route("/bd-dashboard/:id", "routes/bd-dashboard.tsx"),
  route("/test-api", "routes/test-api.tsx"),
] satisfies RouteConfig;
