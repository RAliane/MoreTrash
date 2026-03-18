//! About page - company information

use dioxus::prelude::*;

#[component]
pub fn About() -> Element {
    rsx! {
        main { class: "min-h-screen bg-background",
            section { class: "border-b border-border py-24",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    h1 { class: "text-5xl font-bold text-foreground mb-6",
                        "About Matchgorithm"
                    }
                    p { class: "text-xl text-muted-foreground max-w-3xl",
                        "We're building the future of intelligent matching through evolutionary algorithms and AI."
                    }
                }
            }
            // TODO: Add team, mission, values sections
        }
    }
}
