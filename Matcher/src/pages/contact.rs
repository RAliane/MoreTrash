//! Contact page - contact form with backend submission

use dioxus::prelude::*;

#[component]
pub fn Contact() -> Element {
    let mut name = use_signal(String::new);
    let mut email = use_signal(String::new);
    let mut subject = use_signal(String::new);
    let mut message = use_signal(String::new);
    let mut error = use_signal(|| None::<String>);
    let mut success = use_signal(|| false);
    let mut loading = use_signal(|| false);

    let handle_submit = move |evt: Event<FormData>| {
        evt.prevent_default();
        loading.set(true);
        error.set(None);

        spawn(async move {
            let response = gloo_net::http::Request::post("/api/cms/contact_submissions")
                .header("Content-Type", "application/json")
                .body(
                    serde_json::json!({
                        "name": name(),
                        "email": email(),
                        "subject": subject(),
                        "message": message(),
                        "status": "new"
                    })
                    .to_string(),
                )
                .unwrap()
                .send()
                .await;

            loading.set(false);

            match response {
                Ok(res) if res.ok() => {
                    success.set(true);
                    name.set(String::new());
                    email.set(String::new());
                    subject.set(String::new());
                    message.set(String::new());
                }
                Ok(_) => {
                    error.set(Some(
                        "Failed to send message. Please try again.".to_string(),
                    ));
                }
                Err(e) => {
                    error.set(Some(format!("Network error: {}", e)));
                }
            }
        });
    };

    rsx! {
        main { class: "min-h-screen bg-slate-950",
            // Hero
            section { class: "border-b border-slate-800 py-24",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    h1 { class: "text-5xl font-bold text-white mb-6",
                        "Contact Us"
                    }
                    p { class: "text-xl text-slate-400 max-w-3xl",
                        "Get in touch with our team for demos, support, or partnership inquiries."
                    }
                }
            }

            // Contact Grid
            section { class: "py-24",
                div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    div { class: "grid lg:grid-cols-2 gap-16",
                        // Contact Info
                        div { class: "space-y-8",
                            div {
                                h3 { class: "text-xl font-semibold text-white mb-2", "Email" }
                                p { class: "text-slate-400", "support@matchgorithm.co.uk" }
                            }
                            div {
                                h3 { class: "text-xl font-semibold text-white mb-2", "Location" }
                                p { class: "text-slate-400", "London, United Kingdom" }
                            }
                            div {
                                h3 { class: "text-xl font-semibold text-white mb-2", "Business Hours" }
                                p { class: "text-slate-400", "Monday - Friday: 9am - 6pm GMT" }
                            }
                        }

                        // Contact Form
                        div { class: "bg-slate-900 border border-slate-800 rounded-xl p-8",
                            if success() {
                                div { class: "text-center py-8",
                                    div { class: "w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-4",
                                        svg { class: "w-8 h-8 text-green-500",
                                            xmlns: "http://www.w3.org/2000/svg",
                                            fill: "none",
                                            view_box: "0 0 24 24",
                                            stroke: "currentColor",
                                            stroke_width: "2",
                                            path {
                                                stroke_linecap: "round",
                                                stroke_linejoin: "round",
                                                d: "M5 13l4 4L19 7"
                                            }
                                        }
                                    }
                                    h3 { class: "text-xl font-semibold text-white mb-2",
                                        "Message sent!"
                                    }
                                    p { class: "text-slate-400",
                                        "We'll get back to you within 24 hours."
                                    }
                                    button {
                                        onclick: move |_| success.set(false),
                                        class: "mt-4 text-blue-400 hover:text-blue-300",
                                        "Send another message"
                                    }
                                }
                            } else {
                                h2 { class: "text-2xl font-bold text-white mb-6",
                                    "Send us a message"
                                }

                                if let Some(err) = error() {
                                    div { class: "bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-4",
                                        "{err}"
                                    }
                                }

                                form { onsubmit: handle_submit,
                                    div { class: "space-y-4",
                                        div {
                                            label { class: "block text-sm font-medium text-slate-300 mb-2",
                                                "Name"
                                            }
                                            input {
                                                r#type: "text",
                                                required: true,
                                                class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500",
                                                placeholder: "Your name",
                                                value: "{name}",
                                                oninput: move |evt| name.set(evt.value())
                                            }
                                        }
                                        div {
                                            label { class: "block text-sm font-medium text-slate-300 mb-2",
                                                "Email"
                                            }
                                            input {
                                                r#type: "email",
                                                required: true,
                                                class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500",
                                                placeholder: "name@example.com",
                                                value: "{email}",
                                                oninput: move |evt| email.set(evt.value())
                                            }
                                        }
                                        div {
                                            label { class: "block text-sm font-medium text-slate-300 mb-2",
                                                "Subject"
                                            }
                                            input {
                                                r#type: "text",
                                                required: true,
                                                class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500",
                                                placeholder: "How can we help?",
                                                value: "{subject}",
                                                oninput: move |evt| subject.set(evt.value())
                                            }
                                        }
                                        div {
                                            label { class: "block text-sm font-medium text-slate-300 mb-2",
                                                "Message"
                                            }
                                            textarea {
                                                required: true,
                                                rows: 4,
                                                class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none",
                                                placeholder: "Tell us more about your inquiry...",
                                                value: "{message}",
                                                oninput: move |evt| message.set(evt.value())
                                            }
                                        }
                                        button {
                                            r#type: "submit",
                                            disabled: loading(),
                                            class: "w-full px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-semibold rounded-lg transition",
                                            if loading() { "Sending..." } else { "Send Message" }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
