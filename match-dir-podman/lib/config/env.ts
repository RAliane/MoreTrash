export const config = {
  hasura: {
    endpoint: process.env.HASURA_GRAPHQL_ENDPOINT || "http://localhost:8080/v1/graphql",
    adminSecret: process.env.HASURA_ADMIN_SECRET || "",
    enabled: !!process.env.HASURA_GRAPHQL_ENDPOINT,
  },

  directus: {
    url: process.env.DIRECTUS_URL || "http://localhost:8055",
    token: process.env.DIRECTUS_TOKEN || "",
    enabled: !!process.env.DIRECTUS_URL,
  },

  stripe: {
    secretKey: process.env.STRIPE_SECRET_KEY || "",
    publishableKey: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "",
    enabled: !!process.env.STRIPE_SECRET_KEY,
  },

  n8n: {
    webhookUrl: process.env.N8N_WEBHOOK_URL || "",
    apiUrl: process.env.N8N_API_URL || "",
    enabled: !!process.env.N8N_WEBHOOK_URL,
  },

  email: {
    hunterIoKey: process.env.HUNTER_IO_KEY || "",
    apolloIoKey: process.env.APOLLO_IO_KEY || "",
  },

  analytics: {
    duckdbUrl: process.env.DUCKDB_URL || "",
    mysqlUrl: process.env.DATABASE_URL || "",
  },

  cloudflare: {
    kvNamespace: process.env.CLOUDFLARE_KV_NAMESPACE_ID || "",
    durableObjectName: process.env.DURABLE_OBJECT_NAME || "",
    r2Bucket: process.env.R2_BUCKET_NAME || "",
    d1Database: process.env.D1_DATABASE_ID || "",
  },

  features: {
    automationEnabled: process.env.FEATURE_AUTOMATION === "true",
    analyticsEnabled: process.env.FEATURE_ANALYTICS === "true",
    affiliateEnabled: process.env.FEATURE_AFFILIATE === "true",
  },
}
