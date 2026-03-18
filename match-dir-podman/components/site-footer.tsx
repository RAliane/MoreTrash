import Link from "next/link"

export function SiteFooter() {
  const footerSections = [
    {
      title: "Product",
      links: [
        { label: "Platform", href: "/platform" },
        { label: "Pricing", href: "/pricing" },
        { label: "Solutions", href: "/solutions" },
      ],
    },
    {
      title: "Company",
      links: [
        { label: "About", href: "/about" },
        { label: "Blog", href: "/blog" },
        { label: "Careers", href: "/careers" },
      ],
    },
    {
      title: "Resources",
      links: [
        { label: "Documentation", href: "/docs" },
        { label: "API Reference", href: "/api-docs" },
        { label: "Contact", href: "/contact" },
      ],
    },
    {
      title: "Legal",
      links: [
        { label: "Privacy Policy", href: "/privacy" },
        { label: "Terms of Service", href: "/terms" },
      ],
    },
  ]

  return (
    <footer className="border-t border-border bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid md:grid-cols-5 gap-8 mb-8">
          <div>
            <div className="font-bold text-lg mb-4">Matchgorithm</div>
            <p className="text-muted-foreground text-sm">
              AI-powered professional matching platform connecting talent with opportunity.
            </p>
          </div>
          {footerSections.map((section) => (
            <div key={section.title}>
              <h3 className="font-semibold text-sm mb-4">{section.title}</h3>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href} className="text-muted-foreground hover:text-foreground text-sm transition">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-border pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-muted-foreground text-sm">&copy; 2025 Matchgorithm. All rights reserved.</p>
            <div className="flex gap-4">
              <a
                href="https://twitter.com"
                className="text-muted-foreground hover:text-foreground transition"
                aria-label="Twitter"
              >
                Twitter
              </a>
              <a
                href="https://linkedin.com"
                className="text-muted-foreground hover:text-foreground transition"
                aria-label="LinkedIn"
              >
                LinkedIn
              </a>
              <a
                href="https://github.com"
                className="text-muted-foreground hover:text-foreground transition"
                aria-label="GitHub"
              >
                GitHub
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
