"use client"
import { Button } from "@/components/ui/button"
import { ArrowRight, BarChart3, Lock, Cpu, Database, Workflow } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"

export default function PlatformPage() {
  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      {/* Hero Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="text-center md:text-left max-w-3xl">
              <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6 text-balance">
                The Intelligent Matching Platform
              </h1>
              <p className="text-xl text-muted-foreground mb-8">
                Harness the power of AI to create meaningful professional connections. Our platform combines advanced
                algorithms with human insights to deliver perfect matches every time.
              </p>
            </div>
            <div className="rounded-lg overflow-hidden">
              <img
                src="/ai-platform-dashboard-with-matching-interface.jpg"
                alt="Matchgorithm AI Platform"
                className="w-full h-auto object-cover rounded-lg"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Core Features */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-4xl font-bold text-foreground mb-16 text-center">Core Platform Features</h2>

          <div className="grid md:grid-cols-2 gap-8 mb-16">
            <div className="border border-border rounded-lg p-8 hover:border-primary/50 transition">
              <Cpu className="w-8 h-8 text-primary mb-4" />
              <h3 className="text-2xl font-semibold text-foreground mb-3">AI Matching Engine</h3>
              <p className="text-muted-foreground mb-4">
                Proprietary machine learning algorithms analyze thousands of data points to identify ideal matches based
                on skills, experience, values, and goals.
              </p>
              <a href="#" className="text-primary hover:text-primary/80 flex items-center gap-2 transition">
                Learn more <ArrowRight className="w-4 h-4" />
              </a>
            </div>

            <div className="border border-border rounded-lg p-8 hover:border-primary/50 transition">
              <Database className="w-8 h-8 text-primary mb-4" />
              <h3 className="text-2xl font-semibold text-foreground mb-3">Document Parser</h3>
              <p className="text-muted-foreground mb-4">
                Automatically extract and analyze CVs, portfolios, and professional documents to build comprehensive
                candidate profiles instantly.
              </p>
              <a href="#" className="text-primary hover:text-primary/80 flex items-center gap-2 transition">
                Learn more <ArrowRight className="w-4 h-4" />
              </a>
            </div>

            <div className="border border-border rounded-lg p-8 hover:border-primary/50 transition">
              <BarChart3 className="w-8 h-8 text-primary mb-4" />
              <h3 className="text-2xl font-semibold text-foreground mb-3">Advanced Analytics</h3>
              <p className="text-muted-foreground mb-4">
                Real-time dashboards provide compatibility scores, success metrics, and insights to optimize your
                matching strategy.
              </p>
              <a href="#" className="text-primary hover:text-primary/80 flex items-center gap-2 transition">
                Learn more <ArrowRight className="w-4 h-4" />
              </a>
            </div>

            <div className="border border-border rounded-lg p-8 hover:border-primary/50 transition">
              <Workflow className="w-8 h-8 text-primary mb-4" />
              <h3 className="text-2xl font-semibold text-foreground mb-3">Workflow Automation</h3>
              <p className="text-muted-foreground mb-4">
                Automate matching processes, notifications, and follow-ups with customizable workflows tailored to your
                organization.
              </p>
              <a href="#" className="text-primary hover:text-primary/80 flex items-center gap-2 transition">
                Learn more <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <Lock className="w-12 h-12 text-primary mb-6" />
              <h2 className="text-4xl font-bold text-foreground mb-6">Enterprise-Grade Security</h2>
              <ul className="space-y-4 text-muted-foreground">
                <li className="flex gap-3">
                  <span className="text-primary font-bold">✓</span>
                  <span>End-to-end encryption for all data</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-primary font-bold">✓</span>
                  <span>SOC 2 Type II compliant infrastructure</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-primary font-bold">✓</span>
                  <span>GDPR and data privacy standards</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-primary font-bold">✓</span>
                  <span>Regular security audits and penetration testing</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-primary font-bold">✓</span>
                  <span>24/7 monitoring and incident response</span>
                </li>
              </ul>
            </div>
            <div className="bg-gradient-to-br from-primary/10 to-accent/10 rounded-lg h-96 flex items-center justify-center border border-border">
              <Lock className="w-24 h-24 text-primary opacity-30" />
            </div>
          </div>
        </div>
      </section>

      {/* Integration Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-4xl font-bold text-foreground mb-16 text-center">Seamless Integrations</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {["Slack", "Teams", "Zapier", "Gmail", "Salesforce", "HubSpot", "Calendar", "Notion"].map((integration) => (
              <div
                key={integration}
                className="border border-border rounded-lg p-8 text-center hover:bg-card hover:border-primary/50 transition"
              >
                <p className="font-semibold text-foreground">{integration}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-card border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-6">Ready to transform your matching?</h2>
          <p className="text-xl text-muted-foreground mb-8">
            Experience the future of professional connections with our platform
          </p>
          <div className="flex gap-4 justify-center">
            <Button size="lg">Start Free Trial</Button>
            <Button size="lg" variant="outline">
              Schedule Demo
            </Button>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
