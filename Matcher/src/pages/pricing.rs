//! Pricing page - subscription tiers

use dioxus::prelude::*;

#[component]
pub fn Pricing() -> Element {
    rsx! {
        main { class: "min-h-screen bg-background",
            section { class: "border-b border-border py-24",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    div { class: "text-center mb-16",
                        h1 { class: "text-5xl font-bold text-foreground mb-6",
                            "Simple, Transparent Pricing"
                        }
                        p { class: "text-xl text-muted-foreground",
                            "Choose the plan that fits your needs"
                        }
                    }
                    // TODO: Add pricing cards
                }
            }
        }
    }
}
