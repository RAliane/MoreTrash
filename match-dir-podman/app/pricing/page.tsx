"use client"

import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { Button } from "@/components/ui/button"
import { Check } from "lucide-react"
import Link from "next/link"

export default function PricingPage() {
  const plans = [
    {
      name: "Starter",
      price: "$29",
      period: "/month",
      description: "Perfect for individuals and small teams",
      features: [
        "Up to 50 monthly matches",
        "Basic AI matching",
        "Email support",
        "Standard analytics",
        "Profile management",
      ],
      cta: "Start Free Trial",
      highlighted: false,
    },
    {
      name: "Professional",
      price: "$99",
      period: "/month",
      description: "For growing teams and organizations",
      features: [
        "Unlimited matches",
        "Advanced AI matching",
        "Priority support",
        "Advanced analytics",
        "Team collaboration",
        "Custom integrations",
        "API access",
      ],
      cta: "Get Started",
      highlighted: true,
    },
    {
      name: "Enterprise",
      price: "Custom",
      period: "pricing",
      description: "For large organizations",
      features: [
        "Everything in Professional",
        "Dedicated account manager",
        "Custom AI models",
        "Advanced security",
        "On-premise deployment",
        "SLA guarantees",
        "Custom integrations",
      ],
      cta: "Contact Sales",
      highlighted: false,
    },
  ]

  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      {/* Header */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6">
            <span className="text-balance">Simple, Transparent Pricing</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Choose the perfect plan for your matching needs. Scale as you grow.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-3 gap-8">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-lg border p-8 flex flex-col ${
                  plan.highlighted
                    ? "border-primary bg-card scale-105 md:scale-110"
                    : "border-border hover:border-primary/50"
                } transition`}
              >
                <div className="mb-6">
                  <h3 className="text-2xl font-bold text-foreground mb-2">{plan.name}</h3>
                  <p className="text-muted-foreground text-sm">{plan.description}</p>
                </div>

                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-foreground">{plan.price}</span>
                    <span className="text-muted-foreground">{plan.period}</span>
                  </div>
                </div>

                <Link href="/auth/sign-up" className="mb-6">
                  <Button size="lg" className="w-full" variant={plan.highlighted ? "default" : "outline"}>
                    {plan.cta}
                  </Button>
                </Link>

                <ul className="space-y-3 flex-1">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex gap-3 items-start">
                      <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-3xl font-bold text-foreground mb-12 text-center">Frequently Asked Questions</h2>

          <div className="space-y-6">
            {[
              {
                q: "Can I change plans anytime?",
                a: "Yes, you can upgrade or downgrade your plan at any time. Changes take effect on your next billing cycle.",
              },
              {
                q: "Do you offer a free trial?",
                a: "Yes, all plans include a 14-day free trial. No credit card required to get started.",
              },
              {
                q: "What payment methods do you accept?",
                a: "We accept all major credit cards, PayPal, and bank transfers for Enterprise plans.",
              },
              {
                q: "Is there a minimum commitment?",
                a: "No, you can cancel anytime. Enterprise plans may have custom terms.",
              },
            ].map((faq, i) => (
              <div key={i} className="border border-border rounded-lg p-6">
                <h3 className="font-semibold text-foreground mb-2">{faq.q}</h3>
                <p className="text-muted-foreground">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-card border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-6">Ready to get started?</h2>
          <Link href="/auth/sign-up">
            <Button size="lg">Start Your Free Trial</Button>
          </Link>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
