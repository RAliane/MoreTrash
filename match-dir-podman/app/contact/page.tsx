"use client"

import type React from "react"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { Button } from "@/components/ui/button"
import { Mail, Phone, MapPin, MessageSquare } from "lucide-react"
import { useState } from "react"

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Handle form submission here
    console.log("Form submitted:", formData)
    setFormData({ name: "", email: "", subject: "", message: "" })
  }

  return (
    <main className="min-h-screen bg-background">
      {/* Navigation */}
      <SiteHeader />

      {/* Hero Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6 text-balance">Get in Touch</h1>
              <p className="text-xl text-muted-foreground">
                Have questions? We'd love to hear from you. Send us a message and we'll respond as soon as possible.
              </p>
            </div>
            <img
              src="/customer-support-contact-help-desk-communication.jpg"
              alt="Get in Touch"
              className="rounded-lg w-full h-auto object-cover"
            />
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-12">
            {/* Contact Info */}
            <div>
              <h2 className="text-3xl font-bold text-foreground mb-8">Contact Information</h2>

              <div className="space-y-8">
                <div className="flex gap-4">
                  <Mail className="w-6 h-6 text-primary flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold text-foreground mb-1">Email</h3>
                    <p className="text-muted-foreground">support@matcher.io</p>
                    <p className="text-muted-foreground">sales@matcher.io</p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <Phone className="w-6 h-6 text-primary flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold text-foreground mb-1">Phone</h3>
                    <p className="text-muted-foreground">+1 (555) 123-4567</p>
                    <p className="text-muted-foreground">Mon-Fri, 9am-6pm EST</p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <MapPin className="w-6 h-6 text-primary flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold text-foreground mb-1">Office</h3>
                    <p className="text-muted-foreground">San Francisco, CA</p>
                    <p className="text-muted-foreground">New York, NY</p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <MessageSquare className="w-6 h-6 text-primary flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold text-foreground mb-1">Live Chat</h3>
                    <p className="text-muted-foreground">Available 24/7 on our platform</p>
                    <p className="text-muted-foreground">Average response: 2 minutes</p>
                  </div>
                </div>
              </div>

              <div className="mt-12 p-6 bg-card border border-border rounded-lg">
                <h3 className="font-semibold text-foreground mb-2">Response Time</h3>
                <p className="text-muted-foreground text-sm">
                  We typically respond to all inquiries within 24 hours during business days.
                </p>
              </div>
            </div>

            {/* Contact Form */}
            <div className="border border-border rounded-lg p-8">
              <h2 className="text-3xl font-bold text-foreground mb-8">Send us a Message</h2>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Your name"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="your@email.com"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Subject</label>
                  <input
                    type="text"
                    value={formData.subject}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    className="w-full px-4 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="How can we help?"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Message</label>
                  <textarea
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    className="w-full px-4 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary min-h-32 resize-none"
                    placeholder="Tell us more..."
                    required
                  />
                </div>

                <Button type="submit" size="lg" className="w-full">
                  Send Message
                </Button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h2 className="text-3xl font-bold text-foreground mb-12 text-center">Frequently Asked Questions</h2>

          <div className="space-y-6">
            {[
              {
                q: "What is the pricing structure?",
                a: "We offer flexible plans for startups, enterprises, and everyone in between. Contact sales for custom pricing.",
              },
              {
                q: "Do you offer a free trial?",
                a: "Yes! All plans come with a 14-day free trial. No credit card required to get started.",
              },
              {
                q: "What integrations do you support?",
                a: "We integrate with Slack, Teams, Zapier, Gmail, Salesforce, HubSpot, and many more. Check our docs for the full list.",
              },
              {
                q: "How is my data secured?",
                a: "We use enterprise-grade encryption, regular security audits, and comply with GDPR, SOC 2 Type II, and other standards.",
              },
            ].map((faq, i) => (
              <details
                key={i}
                className="border border-border rounded-lg p-6 cursor-pointer hover:bg-background transition"
              >
                <summary className="font-semibold text-foreground flex items-center justify-between">
                  {faq.q}
                  <span className="text-primary">+</span>
                </summary>
                <p className="text-muted-foreground mt-4">{faq.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <SiteFooter />
    </main>
  )
}
