use dioxus::prelude::*;

#[component]
pub fn Matches() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                div {
                    class: "md:flex md:items-center md:justify-between",
                    div {
                        class: "flex-1 min-w-0",
                        h1 {
                            class: "text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate",
                            "Your Matches"
                        }
                        p {
                            class: "mt-1 text-sm text-gray-500",
                            "View and manage your optimization matches"
                        }
                    }
                    div {
                        class: "mt-4 flex md:mt-0 md:ml-4",
                        button {
                            r#type: "button",
                            class: "inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                            "Run New Optimization"
                        }
                    }
                }

                // Matches grid
                div {
                    class: "mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3",
                    // Placeholder match cards
                    (0..6).map(|i| rsx! {
                        div {
                            class: "bg-white overflow-hidden shadow rounded-lg",
                            div {
                                class: "p-5",
                                div {
                                    class: "flex items-center",
                                    div {
                                        class: "flex-shrink-0",
                                        div {
                                            class: "w-8 h-8 bg-green-500 rounded-full flex items-center justify-center",
                                            span {
                                                class: "text-white text-sm font-medium",
                                                "{i + 1}"
                                            }
                                        }
                                    }
                                    div {
                                        class: "ml-5 w-0 flex-1",
                                        dl {
                                            dt {
                                                class: "text-sm font-medium text-gray-500 truncate",
                                                "Match #{i + 1}"
                                            }
                                            dd {
                                                class: "text-lg font-medium text-gray-900",
                                                "95.{i * 3}% compatibility"
                                            }
                                        }
                                    }
                                }
                            }
                            div {
                                class: "bg-gray-50 px-5 py-3",
                                div {
                                    class: "text-sm",
                                    a {
                                        class: "font-medium text-indigo-600 hover:text-indigo-500",
                                        href: "#",
                                        "View details"
                                    }
                                }
                            }
                        }
                    })
                }

                // Empty state when no matches
                div {
                    class: "mt-8 text-center",
                    div {
                        class: "mx-auto h-12 w-12 text-gray-400",
                        svg {
                            class: "h-12 w-12",
                            fill: "none",
                            stroke: "currentColor",
                            view_box: "0 0 24 24",
                            "aria-hidden": "true",
                            path {
                                stroke_linecap: "round",
                                stroke_linejoin: "round",
                                stroke_width: "2",
                                d: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            }
                        }
                    }
                    h3 {
                        class: "mt-2 text-sm font-medium text-gray-900",
                        "No matches yet"
                    }
                    p {
                        class: "mt-1 text-sm text-gray-500",
                        "Run an optimization to find your best matches."
                    }
                    div {
                        class: "mt-6",
                        button {
                            r#type: "button",
                            class: "inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                            "Start Optimization"
                        }
                    }
                }
            }
        }
    }
}