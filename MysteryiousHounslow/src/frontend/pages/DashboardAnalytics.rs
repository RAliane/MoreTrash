use dioxus::prelude::*;

#[component]
pub fn DashboardAnalytics() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "DashboardAnalytics"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "DashboardAnalytics page coming soon."
                }
            }
        }
    }
}
