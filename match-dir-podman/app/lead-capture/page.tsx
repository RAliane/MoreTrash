"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Card } from "@/components/ui/card"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { CheckCircle2 } from "lucide-react"

export default function LeadCapturePage() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    email: "",
    name: "",
    company: "",
    interests: "",
    phone: "",
  })
  const [submitted, setSubmitted] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const response = await fetch("/api/email/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: formData.email }),
      })

      if (response.ok) {
        setSubmitted(true)
        // Simulate clearing form after success
        setTimeout(() => {
          setFormData({ email: "", name: "", company: "", interests: "", phone: "" })
          setSubmitted(false)
          setStep(1)
        }, 3000)
      }
    } catch (error) {
      console.error("Form submission error:", error)
    }
  }

  if (submitted) {
    return (
      <main className="min-h-screen bg-background">
        <SiteHeader />
        <section className="max-w-2xl mx-auto px-4 py-24">
          <div className="text-center space-y-4">
            <CheckCircle2 className="w-16 h-16 text-primary mx-auto" />
            <h1 className="text-3xl font-bold text-foreground">Thank You!</h1>
            <p className="text-xl text-muted-foreground">
              We've received your information and will be in touch shortly.
            </p>
          </div>
        </section>
        <SiteFooter />
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />
      <section className="max-w-2xl mx-auto px-4 py-16">
        <Card className="p-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">Lead Capture Form</h1>
          <p className="text-muted-foreground mb-8">Tell us about your business and we'll help you automate</p>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Step 1: Contact Info */}
            {step === 1 && (
              <div className="space-y-4 animate-in fade-in duration-300">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Email Address</label>
                  <Input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="your@email.com"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Full Name</label>
                  <Input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="John Doe"
                    required
                  />
                </div>
                <Button type="button" onClick={() => setStep(2)} className="w-full">
                  Next Step
                </Button>
              </div>
            )}

            {/* Step 2: Company Info */}
            {step === 2 && (
              <div className="space-y-4 animate-in fade-in duration-300">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Company Name</label>
                  <Input
                    type="text"
                    name="company"
                    value={formData.company}
                    onChange={handleChange}
                    placeholder="Your Company"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Phone Number</label>
                  <Input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    placeholder="+1 (555) 000-0000"
                  />
                </div>
                <div className="flex gap-4">
                  <Button type="button" onClick={() => setStep(1)} variant="outline" className="flex-1">
                    Back
                  </Button>
                  <Button type="button" onClick={() => setStep(3)} className="flex-1">
                    Next Step
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Interests */}
            {step === 3 && (
              <div className="space-y-4 animate-in fade-in duration-300">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">What are you interested in?</label>
                  <Textarea
                    name="interests"
                    value={formData.interests}
                    onChange={handleChange}
                    placeholder="Tell us about your needs, goals, and challenges..."
                    rows={5}
                  />
                </div>
                <div className="flex gap-4">
                  <Button type="button" onClick={() => setStep(2)} variant="outline" className="flex-1">
                    Back
                  </Button>
                  <Button type="submit" className="flex-1">
                    Submit
                  </Button>
                </div>
              </div>
            )}

            {/* Progress Indicator */}
            <div className="flex gap-2 justify-center mt-8">
              {[1, 2, 3].map((s) => (
                <div
                  key={s}
                  className={`h-2 w-8 rounded-full transition-colors ${step >= s ? "bg-primary" : "bg-border"}`}
                />
              ))}
            </div>
          </form>
        </Card>
      </section>
      <SiteFooter />
    </main>
  )
}
