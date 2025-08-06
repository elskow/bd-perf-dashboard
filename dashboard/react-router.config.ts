import type { Config } from "@react-router/dev/config";

export default {
  // Config options...
  // Server-side render by default, to enable SPA mode set this to `false`
  ssr: false,

  // SPA mode configuration
  basename: "/",

  // Build configuration
  buildDirectory: "build",

  // Static generation options for key routes
  prerender: ["/", "/bd-list"],

  // Public path for assets
  publicPath: "/",

  // Future flags
  future: {
    v3_fetcherPersist: true,
    v3_relativeSplatPath: true,
    v3_throwAbortReason: true,
  },
} satisfies Config;
