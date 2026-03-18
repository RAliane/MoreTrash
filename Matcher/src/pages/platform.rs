//! Platform page - showcases features and capabilities

use dioxus::prelude::*;

#[component]
pub fn Platform() -> Element {
    rsx! {
        main { class: "min-h-screen bg-background",
            // Hero
            section { class: "border-b border-border py-24",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    h1 { class: "text-5xl font-bold text-foreground mb-6",
                        "The Matchgorithm Platform"
                    }
                    p { class: "text-xl text-muted-foreground max-w-3xl",
                        "A comprehensive suite of AI-powered tools for intelligent matching, optimization, and analytics."
                    }
                }
            }
            // TODO: Add platform features, integrations, etc.
        }
    }
}
