"use client"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { Button } from "@/components/ui/button"
import { CheckCircle2, Users, Building2, Briefcase, Zap } from "lucide-react"

export default function SolutionsPage() {
  return (
    <main className="min-h-screen bg-background">
      {/* Navigation */}
      <SiteHeader />

      {/* Hero Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6 text-balance">
              Solutions for Every Team
            </h1>
            <p className="text-xl text-muted-foreground mb-8">
              Whether you're a startup, enterprise, or everything in between, we have solutions tailored to your
              matching needs.
            </p>
          </div>
        </div>
      </section>

      {/* Solution Cards */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="space-y-12">
            {/* Recruitment Solution */}
            <div className="grid md:grid-cols-2 gap-12 items-center border border-border rounded-lg p-8">
              <div>
                <Briefcase className="w-12 h-12 text-primary mb-6" />
                <h2 className="text-3xl font-bold text-foreground mb-4">Recruitment & Talent Matching</h2>
                <p className="text-muted-foreground mb-6">
                  Reduce time-to-hire and find top talent that perfectly fits your organization culture and technical
                  requirements.
                </p>
                <ul className="space-y-3 mb-8">
                  {[
                    "Smart candidate ranking",
                    "Automated screening",
                    "Culture fit analysis",
                    "Skill gap identification",
                  ].map((item) => (
                    <li key={item} className="flex gap-3 text-foreground">
                      <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
                <Button>Learn More</Button>
              </div>
              <img
                src="/recruitment-hiring-process-candidates-screening.jpg"
                alt="Recruitment and Talent Matching"
                className="rounded-lg w-full h-64 object-cover"
              />
            </div>

            {/* Enterprise Collaboration */}
            <div className="grid md:grid-cols-2 gap-12 items-center border border-border rounded-lg p-8">
              <img
                src="/team-collaboration-meeting-working-together.jpg"
                alt="Enterprise Team Collaboration"
                className="rounded-lg w-full h-64 object-cover order-2 md:order-1"
              />
              <div className="order-1 md:order-2">
                <Users className="w-12 h-12 text-primary mb-6" />
                <h2 className="text-3xl font-bold text-foreground mb-4">Enterprise Team Collaboration</h2>
                <p className="text-muted-foreground mb-6">
                  Build high-performing teams by matching employees based on complementary skills, working styles, and
                  project needs.
                </p>
                <ul className="space-y-3 mb-8">
                  {[
                    "Cross-functional team building",
                    "Project-based matching",
                    "Skill complementarity",
                    "Team dynamics analysis",
                  ].map((item) => (
                    <li key={item} className="flex gap-3 text-foreground">
                      <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
                <Button>Learn More</Button>
              </div>
            </div>

            {/* Startup Solutions */}
            <div className="grid md:grid-cols-2 gap-12 items-center border border-border rounded-lg p-8">
              <div>
                <Building2 className="w-12 h-12 text-primary mb-6" />
                <h2 className="text-3xl font-bold text-foreground mb-4">Startup & Scaling Solutions</h2>
                <p className="text-muted-foreground mb-6">
                  Find co-founders, advisors, and early employees who share your vision and can help scale your startup.
                </p>
                <ul className="space-y-3 mb-8">
                  {[
                    "Co-founder matching",
                    "Advisor connections",
                    "Early hire identification",
                    "Equity negotiation guides",
                  ].map((item) => (
                    <li key={item} className="flex gap-3 text-foreground">
                      <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
                <Button>Learn More</Button>
              </div>
              <img
                src="/startup-founders-co-founders-team-brainstorming.jpg"
                alt="Startup and Scaling Solutions"
                className="rounded-lg w-full h-64 object-cover"
              />
            </div>

            {/* Freelance Marketplace */}
            <div className="grid md:grid-cols-2 gap-12 items-center border border-border rounded-lg p-8">
              <img
                src="/freelancer-remote-work-laptop-project.jpg"
                alt="Freelance and Project Matching"
                className="rounded-lg w-full h-64 object-cover order-2 md:order-1"
              />
              <div className="order-1 md:order-2">
                <Zap className="w-12 h-12 text-primary mb-6" />
                <h2 className="text-3xl font-bold text-foreground mb-4">Freelance & Project Matching</h2>
                <p className="text-muted-foreground mb-6">
                  Connect with perfect freelancers and contractors who specialize in your project requirements and
                  values.
                </p>
                <ul className="space-y-3 mb-8">
                  {["Skill-based matching", "Portfolio analysis", "Rate negotiation", "Long-term collaboration"].map(
                    (item) => (
                      <li key={item} className="flex gap-3 text-foreground">
                        <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                        {item}
                      </li>
                    ),
                  )}
                </ul>
                <Button>Learn More</Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-card border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-6">Find the perfect solution for your needs</h2>
          <p className="text-xl text-muted-foreground mb-8">
            Each solution is customizable to fit your organization's unique requirements
          </p>
          <div className="flex gap-4 justify-center">
            <Button size="lg">Start Free Trial</Button>
            <Button size="lg" variant="outline">
              Schedule Demo
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <SiteFooter />
    </main>
  )
}
