import type React from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import "./globals.css"
import { AuthProvider } from "@/lib/auth-context"
import { ThemeProvider } from "@/components/theme-provider"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "AutoAffiliates - Hybrid Automation & Affiliate Marketing Platform",
  description:
    "Complete automation and affiliate marketing system with lead capture, analytics, and integration management. Deploy with Hasura, Directus, Stripe, and n8n.",
  generator: "v0.app",
  metadataBase: new URL("https://www.autoaffiliates.com"),
  keywords: [
    "automation platform",
    "affiliate marketing",
    "lead generation",
    "CRM integration",
    "marketing automation",
    "campaign analytics",
  ],
  authors: [{ name: "AutoAffiliates Team" }],
  applicationName: "AutoAffiliates",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
  },
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    type: "website",
    locale: "en_GB",
    url: "https://www.autoaffiliates.com",
    siteName: "AutoAffiliates",
    title: "AutoAffiliates - Hybrid Automation & Affiliate Marketing Platform",
    description:
      "Complete automation and affiliate marketing system with lead capture, analytics, and integration management.",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "AutoAffiliates - Hybrid Automation & Affiliate Marketing Platform",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    site: "@autoaffiliates",
    title: "AutoAffiliates - Hybrid Automation & Affiliate Marketing Platform",
    description:
      "Complete automation and affiliate marketing system with lead capture, analytics, and integration management.",
    images: ["/og-image.jpg"],
  },
  verification: {
    google: "google-site-verification-code",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* DNS prefetch for external services */}
        <link rel="dns-prefetch" href="https://cdn.vercel-analytics.com" />
      </head>
      <body className={`${_geist.className} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <AuthProvider>{children}</AuthProvider>
          <Analytics />
        </ThemeProvider>
      </body>
    </html>
  )
}
