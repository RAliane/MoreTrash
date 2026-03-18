//! Card component

use dioxus::prelude::*;

#[component]
pub fn Card(class: Option<String>, children: Element) -> Element {
    let extra = class.unwrap_or_default();
    rsx! {
        div { class: "border border-border rounded-lg bg-card p-6 {extra}",
            {children}
        }
    }
}
