"use client"

import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-8">Privacy Policy</h1>
          <p className="text-muted-foreground mb-8">Last updated: January 2025</p>

          <div className="prose prose-invert max-w-none space-y-8 text-muted-foreground">
            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">1. Introduction</h2>
              <p>
                Matchgorithm ("we", "our", or "us") operates the Matchgorithm.co.uk website and Matchgorithm matching
                platform (the "Service"). This page informs you of our policies regarding the collection, use, and
                disclosure of personal data when you use our Service and the choices you have associated with that data.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">2. Information Collection</h2>
              <p>
                We collect several different types of information for various purposes to provide and improve our
                Service to you.
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>
                  Personal Data: While using our Service, we may ask you to provide us with certain personally
                  identifiable information that can be used to contact or identify you ("Personal Data").
                </li>
                <li>
                  Usage Data: We may also collect information on how the Service is accessed and used ("Usage Data").
                </li>
                <li>
                  Cookies: We use cookies and similar tracking technologies to track activity on our Service and store
                  certain information.
                </li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">3. Use of Data</h2>
              <p>Matchgorithm uses the collected data for various purposes:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>To provide and maintain our Service</li>
                <li>To notify you about changes to our Service</li>
                <li>To allow you to participate in interactive features of our Service</li>
                <li>To provide customer support</li>
                <li>To gather analysis or valuable information so we can improve our Service</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">4. Security of Data</h2>
              <p>
                The security of your data is important to us but remember that no method of transmission over the
                Internet or method of electronic storage is 100% secure. While we strive to use commercially acceptable
                means to protect your Personal Data, we cannot guarantee its absolute security.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">5. Contact Us</h2>
              <p>
                If you have any questions about this Privacy Policy, please contact us at support@matchgorithm.co.uk or
                by mail at: Matchgorithm Inc., Privacy Department, [Address].
              </p>
            </section>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
