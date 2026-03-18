"use client"

import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { MapPin, Briefcase } from "lucide-react"

export default function CareersPage() {
  const openPositions = [
    {
      id: 1,
      title: "Senior AI/ML Engineer",
      department: "Engineering",
      location: "San Francisco, CA",
      type: "Full-time",
      description: "Help build the next generation of AI matching algorithms.",
    },
    {
      id: 2,
      title: "Product Manager",
      department: "Product",
      location: "New York, NY",
      type: "Full-time",
      description: "Lead the product vision for our matching platform.",
    },
    {
      id: 3,
      title: "Full Stack Engineer",
      department: "Engineering",
      location: "Remote",
      type: "Full-time",
      description: "Build scalable backend systems and modern frontends.",
    },
    {
      id: 4,
      title: "Sales Development Representative",
      department: "Sales",
      location: "Remote",
      type: "Full-time",
      description: "Drive growth by building relationships with enterprise customers.",
    },
  ]

  const benefits = [
    { icon: "🏥", title: "Health Insurance", desc: "Comprehensive medical, dental, and vision coverage" },
    { icon: "💰", title: "Competitive Salary", desc: "Top-of-market compensation packages" },
    { icon: "📈", title: "Equity", desc: "Ownership stake in the company" },
    { icon: "🏠", title: "Remote First", desc: "Work from anywhere in the world" },
    { icon: "🎓", title: "Learning Budget", desc: "$1,500 annual professional development" },
    { icon: "✈️", title: "Unlimited PTO", desc: "Flexible time off policy" },
  ]

  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      {/* Header */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6 text-balance">Join Our Team</h1>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto md:mx-0">
                Help us build the future of professional matching. We're looking for talented, passionate people to join
                our mission.
              </p>
            </div>
            <img
              src="/team-working-together-diverse-office-culture.jpg"
              alt="Join Our Team"
              className="rounded-lg w-full h-auto object-cover"
            />
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-3xl font-bold text-foreground mb-12 text-center">Why Join Matcher?</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {benefits.map((benefit) => (
              <div key={benefit.title} className="border border-border rounded-lg p-8 text-center">
                <div className="text-4xl mb-4">{benefit.icon}</div>
                <h3 className="text-lg font-semibold text-foreground mb-2">{benefit.title}</h3>
                <p className="text-muted-foreground text-sm">{benefit.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Open Positions */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-3xl font-bold text-foreground mb-12">Open Positions</h2>

          <div className="space-y-4">
            {openPositions.map((position) => (
              <div
                key={position.id}
                className="border border-border rounded-lg p-6 hover:border-primary/50 transition group"
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-semibold text-foreground group-hover:text-primary transition">
                      {position.title}
                    </h3>
                    <p className="text-muted-foreground text-sm mb-3 mt-1">{position.description}</p>

                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Briefcase className="w-4 h-4" />
                        {position.department}
                      </div>
                      <div className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        {position.location}
                      </div>
                      <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs">{position.type}</span>
                    </div>
                  </div>

                  <Button className="md:flex-shrink-0">Apply Now</Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Culture Section */}
      <section className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-3xl font-bold text-foreground mb-8">Our Culture</h2>
          <div className="space-y-4 text-muted-foreground">
            <p>
              At Matcher, we believe that the best teams are built on diversity, inclusivity, and a shared commitment to
              excellence. We're building a company where everyone feels valued, empowered, and inspired to do their best
              work.
            </p>
            <p>
              We foster a culture of continuous learning, experimentation, and growth. We encourage our team members to
              take on new challenges, share ideas, and collaborate across teams to solve complex problems.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-3xl font-bold text-foreground mb-4">Don't see a position that fits?</h2>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
            We're always looking for talented people. Send us your resume and let us know what you're interested in.
          </p>
          <Link href="/contact">
            <Button size="lg">Get in Touch</Button>
          </Link>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
