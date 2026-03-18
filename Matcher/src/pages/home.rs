//! Home page component
//!
//! Renders the main landing page with hero, stats, features, and CTA sections.

use dioxus::prelude::*;

/// Home page component
#[component]
pub fn Home() -> Element {
    rsx! {
        main { class: "min-h-screen bg-background",
            // Hero Section
            section { class: "border-b border-border",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 grid md:grid-cols-2 gap-12 items-center",
                    div { class: "space-y-6",
                        h1 { class: "text-5xl md:text-6xl font-bold text-foreground leading-tight",
                            span { class: "text-balance",
                                "AI-Powered Matching Through Evolutionary Algorithms"
                            }
                        }
                        p { class: "text-xl text-muted-foreground",
                            "Matchgorithm uses advanced AI and evolutionary algorithms to provide users with optimized choices. Connect professionals, talent, and opportunities with unprecedented accuracy."
                        }
                        div { class: "flex gap-4",
                            a {
                                href: "/auth/sign-up",
                                class: "px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition font-semibold",
                                "Start Matching Today"
                            }
                            button {
                                class: "px-6 py-3 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition font-semibold",
                                "Watch Demo"
                            }
                        }
                    }
                    div { class: "bg-gradient-to-br from-primary/10 to-accent/10 rounded-lg h-96 flex items-center justify-center border border-border",
                        div { class: "text-center",
                            p { class: "text-muted-foreground", "Evolutionary Matching Algorithm" }
                        }
                    }
                }
            }

            // Stats Section
            section { class: "border-b border-border",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12",
                    div { class: "grid grid-cols-1 md:grid-cols-4 gap-8",
                        StatCard { value: "100K+", label: "Matches Made Daily" }
                        StatCard { value: "99.9%", label: "Enterprise Uptime" }
                        StatCard { value: "50+", label: "Integrations" }
                        StatCard { value: "$10B+", label: "Value Created" }
                    }
                }
            }

            // Features Section
            section { class: "border-b border-border",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24",
                    div { class: "text-center mb-16",
                        h2 { class: "text-4xl font-bold text-foreground mb-4",
                            "Evolutionary Matching Technology"
                        }
                        p { class: "text-xl text-muted-foreground max-w-2xl mx-auto",
                            "Industry-leading algorithms that optimize outcomes for professionals, businesses, and institutions worldwide."
                        }
                    }
                    div { class: "grid md:grid-cols-3 gap-8",
                        FeatureCard {
                            title: "Intelligent Matching",
                            description: "AI-powered profile analysis and matching"
                        }
                        FeatureCard {
                            title: "Evolutionary Algorithms",
                            description: "Continuous optimization of match quality"
                        }
                        FeatureCard {
                            title: "Advanced Analytics",
                            description: "Real-time insights and performance tracking"
                        }
                        FeatureCard {
                            title: "High Performance",
                            description: "Sub-millisecond matching at scale"
                        }
                        FeatureCard {
                            title: "Enterprise Integration",
                            description: "Seamless API and workflow integration"
                        }
                        FeatureCard {
                            title: "Continuous Learning",
                            description: "Adaptive algorithms that improve over time"
                        }
                    }
                }
            }

            // CTA Section
            section { class: "bg-card border-t border-border",
                div { class: "max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center",
                    h2 { class: "text-4xl font-bold text-foreground mb-6",
                        "Experience Next-Gen Matching"
                    }
                    p { class: "text-xl text-muted-foreground mb-8",
                        "Join thousands of organizations using Matchgorithm to optimize their talent and business outcomes"
                    }
                    div { class: "flex gap-4 justify-center",
                        a {
                            href: "/auth/sign-up",
                            class: "px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition font-semibold",
                            "Get Started Free"
                        }
                        button {
                            class: "px-6 py-3 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition font-semibold",
                            "Schedule Demo"
                        }
                    }
                }
            }
        }
    }
}

#[component]
fn StatCard(value: &'static str, label: &'static str) -> Element {
    rsx! {
        div { class: "border-l border-border pl-4",
            div { class: "text-3xl font-bold text-primary", "{value}" }
            p { class: "text-muted-foreground text-sm mt-2", "{label}" }
        }
    }
}

#[component]
fn FeatureCard(title: &'static str, description: &'static str) -> Element {
    rsx! {
        div { class: "border border-border rounded-lg p-8 hover:bg-card transition",
            h3 { class: "text-xl font-semibold text-foreground mb-2", "{title}" }
            p { class: "text-muted-foreground", "{description}" }
        }
    }
}
