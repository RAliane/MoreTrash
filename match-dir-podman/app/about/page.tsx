"use client"
import { Button } from "@/components/ui/button"
import { Heart, Globe, Lightbulb } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-background">
      {/* Navigation */}
      <SiteHeader />

      {/* Hero Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6 text-balance">About Matchgorithm</h1>
            <p className="text-xl text-muted-foreground">
              We're on a mission to transform how professionals connect, collaborate, and grow together.
            </p>
          </div>
        </div>
      </section>

      {/* Story Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-4xl font-bold text-foreground mb-6">Our Story</h2>
              <p className="text-muted-foreground mb-6 leading-relaxed">
                Matchgorithm was founded in 2014 by a team of seasoned professionals frustrated with outdated hiring and
                team-building processes. We realized that the best matches happen when AI and human insight work
                together.
              </p>
              <p className="text-muted-foreground mb-6 leading-relaxed">
                Our founding team brought together expertise in artificial intelligence, human resources, and
                professional development to create a platform that truly understands what makes great matches.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                Today, Matchgorithm helps thousands of organizations and individuals find their perfect professional
                connections every single day.
              </p>
            </div>
            <img src="/company-founders-team-diversity-innovation-mission.jpg" alt="Our Story" className="rounded-lg w-full h-auto object-cover" />
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-4xl font-bold text-foreground mb-16 text-center">Our Values</h2>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="border border-border rounded-lg p-8">
              <Lightbulb className="w-12 h-12 text-primary mb-4" />
              <h3 className="text-2xl font-semibold text-foreground mb-3">Innovation First</h3>
              <p className="text-muted-foreground">
                We constantly push the boundaries of what's possible in AI-powered matching, staying ahead of industry
                trends and delivering cutting-edge solutions.
              </p>
            </div>

            <div className="border border-border rounded-lg p-8">
              <Heart className="w-12 h-12 text-primary mb-4" />
              <h3 className="text-2xl font-semibold text-foreground mb-3">People-Centric</h3>
              <p className="text-muted-foreground">
                We believe in the power of human connections. Our technology is designed to enhance relationships, not
                replace them.
              </p>
            </div>

            <div className="border border-border rounded-lg p-8">
              <Globe className="w-12 h-12 text-primary mb-4" />
              <h3 className="text-2xl font-semibold text-foreground mb-3">Global Accessibility</h3>
              <p className="text-muted-foreground">
                We're committed to making professional matching accessible to everyone, regardless of location,
                background, or circumstances.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-4xl font-bold text-foreground mb-16 text-center">Leadership Team</h2>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              { name: "Alex Johnson", title: "CEO & Co-founder" },
              { name: "Sarah Chen", title: "CTO & Co-founder" },
              { name: "Marcus Williams", title: "Head of Product" },
              { name: "Elena Rodriguez", title: "VP of Operations" },
            ].map((member) => (
              <div
                key={member.name}
                className="border border-border rounded-lg p-6 text-center hover:bg-background transition"
              >
                <div className="bg-gradient-to-br from-primary/10 to-accent/10 rounded-lg h-32 mb-4 flex items-center justify-center border border-border">
                  <div className="text-primary font-bold text-lg">Photo</div>
                </div>
                <h3 className="text-lg font-semibold text-foreground">{member.name}</h3>
                <p className="text-muted-foreground">{member.title}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { stat: "50K+", label: "Successful Matches" },
              { stat: "95%", label: "Satisfaction Rate" },
              { stat: "500+", label: "Enterprise Clients" },
              { stat: "30+", label: "Countries Served" },
            ].map((item) => (
              <div key={item.label} className="text-center">
                <div className="text-4xl font-bold text-primary mb-2">{item.stat}</div>
                <p className="text-muted-foreground">{item.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-card border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-6">Join our community</h2>
          <p className="text-xl text-muted-foreground mb-8">Be part of the professional matching revolution</p>
          <div className="flex gap-4 justify-center">
            <Button size="lg">Get Started</Button>
            <Button size="lg" variant="outline">
              View Careers
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <SiteFooter />
    </main>
  )
}
