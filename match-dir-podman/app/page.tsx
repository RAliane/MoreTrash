"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Zap, BarChart3, Workflow, Users, MessageSquare, TrendingUp } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      {/* Hero Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 grid md:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <h1 className="text-5xl md:text-6xl font-bold text-foreground leading-tight">
              <span className="text-balance">Automate & Monetize Your Marketing</span>
            </h1>
            <p className="text-xl text-muted-foreground">
              Complete hybrid automation and affiliate marketing platform. Capture leads, track campaigns, and scale
              your business with powerful integrations.
            </p>
            <div className="flex gap-4">
              <Link href="/auth/sign-up">
                <Button size="lg">Start Free Trial</Button>
              </Link>
              <Button size="lg" variant="outline">
                Watch Demo
              </Button>
            </div>
          </div>
          <div className="bg-gradient-to-br from-primary/10 to-accent/10 rounded-lg h-96 flex items-center justify-center border border-border">
            <div className="text-center">
              <Workflow className="w-24 h-24 text-primary mx-auto mb-4 opacity-30" />
              <p className="text-muted-foreground">Automation Flow Visualization</p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { label: "10M+ Leads", value: "Processed monthly" },
              { label: "98% Uptime", value: "Enterprise reliability" },
              { label: "50+ Integrations", value: "Pre-built connectors" },
              { label: "$5B+ Revenue", value: "Tracked through platform" },
            ].map((stat) => (
              <div key={stat.label} className="border-l border-border pl-4">
                <div className="text-3xl font-bold text-primary">{stat.label}</div>
                <p className="text-muted-foreground text-sm mt-2">{stat.value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Core Features */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-foreground mb-4">
              <span className="text-balance">All-In-One Marketing Automation</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Everything you need to capture leads, automate workflows, and scale your affiliate business
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: MessageSquare, title: "Lead Capture", desc: "Multi-step forms with email verification" },
              { icon: Workflow, title: "Automation", desc: "n8n webhooks and workflow automation" },
              { icon: BarChart3, title: "Analytics", desc: "Real-time campaign tracking & reporting" },
              { icon: Zap, title: "Integrations", desc: "Hasura, Directus, Stripe, and more" },
              { icon: Users, title: "CRM Sync", desc: "Automatic lead synchronization" },
              { icon: TrendingUp, title: "Growth Tools", desc: "Hunter.io and Apollo.io integration" },
            ].map((feature) => (
              <div key={feature.title} className="border border-border rounded-lg p-8 hover:bg-card transition">
                <feature.icon className="w-8 h-8 text-primary mb-4" />
                <h3 className="text-xl font-semibold text-foreground mb-2">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-foreground mb-4">Trusted by Top Teams</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { name: "Sarah Chen", role: "Marketing Director", text: "Saved us 20+ hours per week with automation" },
              { name: "James Wilson", role: "Growth Manager", text: "Best ROI investment for our team" },
              { name: "Emma Thompson", role: "CEO", text: "Scaled to 10x leads without hiring more staff" },
            ].map((testimonial) => (
              <div key={testimonial.name} className="border border-border rounded-lg p-6 bg-card">
                <p className="text-muted-foreground mb-4">"{testimonial.text}"</p>
                <div>
                  <p className="font-semibold text-foreground">{testimonial.name}</p>
                  <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-card border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-6">Ready to automate your marketing?</h2>
          <p className="text-xl text-muted-foreground mb-8">
            Join hundreds of teams automating their affiliate and lead generation operations
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/auth/sign-up">
              <Button size="lg">Start Free Trial</Button>
            </Link>
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
