//! Site footer component

use dioxus::prelude::*;

#[component]
pub fn Footer() -> Element {
    rsx! {
        footer { class: "border-t border-border bg-background",
            div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12",
                div { class: "grid grid-cols-2 md:grid-cols-4 gap-8",
                    // Product
                    div {
                        h3 { class: "font-semibold text-foreground mb-4", "Product" }
                        nav { class: "space-y-2",
                            a { href: "/platform", class: "block text-muted-foreground hover:text-foreground", "Platform" }
                            a { href: "/pricing", class: "block text-muted-foreground hover:text-foreground", "Pricing" }
                            a { href: "/docs", class: "block text-muted-foreground hover:text-foreground", "Documentation" }
                        }
                    }
                    // Company
                    div {
                        h3 { class: "font-semibold text-foreground mb-4", "Company" }
                        nav { class: "space-y-2",
                            a { href: "/about", class: "block text-muted-foreground hover:text-foreground", "About" }
                            a { href: "/careers", class: "block text-muted-foreground hover:text-foreground", "Careers" }
                            a { href: "/contact", class: "block text-muted-foreground hover:text-foreground", "Contact" }
                        }
                    }
                    // Legal
                    div {
                        h3 { class: "font-semibold text-foreground mb-4", "Legal" }
                        nav { class: "space-y-2",
                            a { href: "/privacy", class: "block text-muted-foreground hover:text-foreground", "Privacy" }
                            a { href: "/terms", class: "block text-muted-foreground hover:text-foreground", "Terms" }
                        }
                    }
                    // Connect
                    div {
                        h3 { class: "font-semibold text-foreground mb-4", "Connect" }
                        p { class: "text-muted-foreground", "support@matchgorithm.co.uk" }
                    }
                }
                // Copyright
                div { class: "mt-12 pt-8 border-t border-border",
                    p { class: "text-center text-muted-foreground text-sm",
                        "© 2026 Matchgorithm. All rights reserved."
                    }
                }
            }
        }
    }
}
