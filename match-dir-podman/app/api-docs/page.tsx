"use client"

import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { Button } from "@/components/ui/button"
import Link from "next/link"

export default function ApiDocsPage() {
  const endpoints = [
    {
      method: "POST",
      path: "/api/matcher/analyze",
      description: "Analyze a user profile and generate match recommendations",
      params: ["userId", "industry", "skills"],
    },
    {
      method: "POST",
      path: "/api/documents/parse",
      description: "Parse and extract information from documents",
      params: ["file", "documentType"],
    },
    {
      method: "GET",
      path: "/api/matcher/compare",
      description: "Compare compatibility between two profiles",
      params: ["profileId1", "profileId2"],
    },
    {
      method: "POST",
      path: "/api/workflows/trigger",
      description: "Trigger an automation workflow",
      params: ["workflowId", "data"],
    },
  ]

  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      {/* Header */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6">API Reference</h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            RESTful API for building with Matcher. Integrate matching capabilities into your applications.
          </p>
        </div>
      </section>

      {/* Authentication */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-3xl font-bold text-foreground mb-8">Authentication</h2>
          <div className="border border-border rounded-lg p-8 bg-card">
            <p className="text-muted-foreground mb-6">
              All API requests require an API key passed in the Authorization header:
            </p>
            <pre className="bg-background rounded p-4 text-sm text-muted-foreground overflow-x-auto">
              <code>{`Authorization: Bearer YOUR_API_KEY\nContent-Type: application/json`}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* Endpoints */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-3xl font-bold text-foreground mb-12">Endpoints</h2>

          <div className="space-y-6">
            {endpoints.map((endpoint, i) => (
              <div key={i} className="border border-border rounded-lg p-8">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <span
                        className={`px-3 py-1 rounded text-xs font-semibold ${
                          endpoint.method === "GET"
                            ? "bg-blue-500/20 text-blue-400"
                            : endpoint.method === "POST"
                              ? "bg-green-500/20 text-green-400"
                              : "bg-orange-500/20 text-orange-400"
                        }`}
                      >
                        {endpoint.method}
                      </span>
                      <code className="text-foreground font-mono">{endpoint.path}</code>
                    </div>
                    <p className="text-muted-foreground">{endpoint.description}</p>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-border">
                  <p className="text-sm font-semibold text-foreground mb-2">Parameters:</p>
                  <ul className="space-y-1">
                    {endpoint.params.map((param) => (
                      <li key={param} className="text-sm text-muted-foreground">
                        • {param}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Rate Limiting */}
      <section className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-3xl font-bold text-foreground mb-8">Rate Limiting</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              { plan: "Starter", requests: "100/minute" },
              { plan: "Professional", requests: "1,000/minute" },
              { plan: "Enterprise", requests: "Unlimited" },
            ].map((limit) => (
              <div key={limit.plan} className="border border-border rounded-lg p-6">
                <h3 className="font-semibold text-foreground mb-2">{limit.plan}</h3>
                <p className="text-muted-foreground">{limit.requests} requests</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-6">Ready to integrate?</h2>
          <div className="flex gap-4 justify-center">
            <Link href="/auth/sign-up">
              <Button size="lg">Get API Key</Button>
            </Link>
            <Link href="/docs">
              <Button size="lg" variant="outline">
                View Docs
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
