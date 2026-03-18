"use client"

import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { Button } from "@/components/ui/button"
import { BookOpen, Code2, Database, Zap } from "lucide-react"
import Link from "next/link"

export default function DocsPage() {
  const docSections = [
    {
      icon: BookOpen,
      title: "Getting Started",
      description: "Learn how to set up and configure Matcher for your organization",
      items: ["Installation", "Quick Start", "Configuration", "First Match"],
    },
    {
      icon: Code2,
      title: "API Reference",
      description: "Complete API documentation with examples and best practices",
      items: ["Authentication", "Endpoints", "Rate Limiting", "Error Handling"],
    },
    {
      icon: Database,
      title: "Data & Security",
      description: "Understand data handling, privacy, and security features",
      items: ["Data Model", "Security", "GDPR", "Compliance"],
    },
    {
      icon: Zap,
      title: "Advanced Features",
      description: "Explore advanced features and customization options",
      items: ["Custom Workflows", "Webhooks", "Integrations", "Analytics"],
    },
  ]

  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      {/* Header */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="text-center md:text-left">
              <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6">Documentation</h1>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto md:mx-0">
                Everything you need to know to build with Matcher. Comprehensive guides, API reference, and examples.
              </p>
            </div>
            <img
              src="/developer-documentation-code-technical-guide.jpg"
              alt="Documentation"
              className="rounded-lg w-full h-auto object-cover"
            />
          </div>
        </div>
      </section>

      {/* Search & Quick Links */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="mb-8">
            <input
              type="search"
              placeholder="Search documentation..."
              className="w-full px-4 py-3 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {["Getting Started", "API Docs", "Examples", "FAQ"].map((link) => (
              <button
                key={link}
                className="px-4 py-2 rounded-lg border border-border hover:bg-card hover:border-primary/50 transition text-sm text-foreground"
              >
                {link}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Documentation Sections */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-8">
            {docSections.map((section) => (
              <div
                key={section.title}
                className="border border-border rounded-lg p-8 hover:border-primary/50 transition"
              >
                <section.icon className="w-10 h-10 text-primary mb-4" />
                <h3 className="text-2xl font-semibold text-foreground mb-2">{section.title}</h3>
                <p className="text-muted-foreground mb-6">{section.description}</p>
                <ul className="space-y-2 mb-6">
                  {section.items.map((item) => (
                    <li key={item} className="text-sm text-muted-foreground hover:text-foreground transition">
                      → {item}
                    </li>
                  ))}
                </ul>
                <Link href="/api-docs">
                  <Button variant="outline" size="sm">
                    Learn more
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Code Examples */}
      <section className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-4xl font-bold text-foreground mb-12 text-center">Popular Examples</h2>

          <div className="space-y-8">
            {[
              { language: "Python", title: "Create a Match" },
              { language: "JavaScript", title: "Upload Document" },
              { language: "cURL", title: "API Authentication" },
            ].map((example) => (
              <div key={example.title} className="border border-border rounded-lg p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold text-foreground">{example.title}</h3>
                  <span className="text-xs bg-primary/10 text-primary px-3 py-1 rounded">{example.language}</span>
                </div>
                <pre className="bg-background rounded p-4 text-sm text-muted-foreground overflow-x-auto">
                  <code>{`# Example code here\nconst matcher = new Matcher();\nmatcher.createMatch(data);`}</code>
                </pre>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-6">Still have questions?</h2>
          <Link href="/contact">
            <Button size="lg">Contact Support</Button>
          </Link>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
