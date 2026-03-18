//! Button component

use dioxus::prelude::*;

#[derive(PartialEq, Clone)]
pub enum ButtonVariant {
    Primary,
    Secondary,
    Outline,
    Ghost,
}

#[component]
pub fn Button(variant: Option<ButtonVariant>, class: Option<String>, children: Element) -> Element {
    let base = "px-4 py-2 rounded-lg font-medium transition";
    let variant_class = match variant.unwrap_or(ButtonVariant::Primary) {
        ButtonVariant::Primary => "bg-primary text-primary-foreground hover:bg-primary/90",
        ButtonVariant::Secondary => "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ButtonVariant::Outline => "border border-border bg-transparent hover:bg-muted",
        ButtonVariant::Ghost => "bg-transparent hover:bg-muted",
    };
    let extra = class.unwrap_or_default();

    rsx! {
        button { class: "{base} {variant_class} {extra}",
            {children}
        }
    }
}
