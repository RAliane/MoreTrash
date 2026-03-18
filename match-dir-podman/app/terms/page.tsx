"use client"

import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-8">Terms of Service</h1>
          <p className="text-muted-foreground mb-8">Last updated: January 2025</p>

          <div className="prose prose-invert max-w-none space-y-8 text-muted-foreground">
            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">1. Agreement to Terms</h2>
              <p>
                By accessing and using the Matchgorithm platform, you accept and agree to be bound by the terms and
                provision of this agreement. If you do not agree to abide by the above, please do not use this service.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">2. Use License</h2>
              <p>
                Permission is granted to temporarily download one copy of the materials (information or software) on
                Matchgorithm's platform for personal, non-commercial transitory viewing only. This is the grant of a
                license, not a transfer of title, and under this license you may not:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Modifying or copying the materials</li>
                <li>Using the materials for any commercial purpose or for any public display</li>
                <li>Attempting to decompile or reverse engineer any software contained on Matchgorithm's platform</li>
                <li>Removing any copyright or other proprietary notations from the materials</li>
                <li>Transferring the materials to another person or "mirroring" the materials on any other server</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">3. Disclaimer</h2>
              <p>
                The materials on Matchgorithm's platform are provided on an 'as is' basis. Matchgorithm makes no
                warranties, expressed or implied, and hereby disclaims and negates all other warranties including,
                without limitation, implied warranties or conditions of merchantability, fitness for a particular
                purpose, or non-infringement of intellectual property or other violation of rights.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">4. Limitations</h2>
              <p>
                In no event shall Matchgorithm or its suppliers be liable for any damages (including, without
                limitation, damages for loss of data or profit, or due to business interruption) arising out of the use
                or inability to use the materials on Matchgorithm's platform, even if Matchgorithm or an authorized
                representative has been notified orally or in writing of the possibility of such damage.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">5. Accuracy of Materials</h2>
              <p>
                The materials appearing on Matchgorithm's platform could include technical, typographical, or
                photographic errors. Matchgorithm does not warrant that any of the materials on its platform are
                accurate, complete, or current. Matchgorithm may make changes to the materials contained on its platform
                at any time without notice.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">6. Links</h2>
              <p>
                Matchgorithm has not reviewed all of the sites linked to its platform and is not responsible for the
                contents of any such linked site. The inclusion of any link does not imply endorsement by Matchgorithm
                of the site. Use of any such linked website is at the user's own risk.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">7. Modifications</h2>
              <p>
                Matchgorithm may revise these terms of service for its platform at any time without notice. By using
                this platform, you are agreeing to be bound by the then current version of these terms of service.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-foreground mb-4">8. Governing Law</h2>
              <p>
                These terms and conditions are governed by and construed in accordance with the laws of the jurisdiction
                in which Matchgorithm operates, and you irrevocably submit to the exclusive jurisdiction of the courts
                in that location.
              </p>
            </section>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
