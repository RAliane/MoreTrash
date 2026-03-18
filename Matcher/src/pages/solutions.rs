//! Solutions page - industry-specific use cases

use dioxus::prelude::*;

#[component]
pub fn Solutions() -> Element {
    rsx! {
        main { class: "min-h-screen bg-background",
            section { class: "border-b border-border py-24",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    h1 { class: "text-5xl font-bold text-foreground mb-6",
                        "Solutions"
                    }
                    p { class: "text-xl text-muted-foreground max-w-3xl",
                        "Tailored matching solutions for every industry and use case."
                    }
                }
            }
            // TODO: Add solution cards for Recruitment, Enterprise, Academic, Freelance
        }
    }
}
