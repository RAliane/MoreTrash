use dioxus::prelude::*;

#[component]
pub fn AdminDashboard() -> Element {
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
                            "Admin Dashboard"
                        }
                        p {
                            class: "mt-1 text-sm text-gray-500",
                            "System administration and monitoring"
                        }
                    }
                }

                // Admin stats cards
                div {
                    class: "mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4",
                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    svg {
                                        class: "h-6 w-6 text-gray-400",
                                        fill: "none",
                                        stroke: "currentColor",
                                        view_box: "0 0 24 24",
                                        "aria-hidden": "true",
                                        path {
                                            stroke_linecap: "round",
                                            stroke_linejoin: "round",
                                            stroke_width: "2",
                                            d: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"
                                        }
                                    }
                                }
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "Total Users"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-gray-900",
                                            "1,234"
                                        }
                                    }
                                }
                            }
                        }
                    }

                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    svg {
                                        class: "h-6 w-6 text-gray-400",
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
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "Active Items"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-gray-900",
                                            "5,678"
                                        }
                                    }
                                }
                            }
                        }
                    }

                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    svg {
                                        class: "h-6 w-6 text-gray-400",
                                        fill: "none",
                                        stroke: "currentColor",
                                        view_box: "0 0 24 24",
                                        "aria-hidden": "true",
                                        path {
                                            stroke_linecap: "round",
                                            stroke_linejoin: "round",
                                            stroke_width: "2",
                                            d: "M13 10V3L4 14h7v7l9-11h-7z"
                                        }
                                    }
                                }
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "Optimizations Today"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-gray-900",
                                            "89"
                                        }
                                    }
                                }
                            }
                        }
                    }

                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    svg {
                                        class: "h-6 w-6 text-gray-400",
                                        fill: "none",
                                        stroke: "currentColor",
                                        view_box: "0 0 24 24",
                                        "aria-hidden": "true",
                                        path {
                                            stroke_linecap: "round",
                                            stroke_linejoin: "round",
                                            stroke_width: "2",
                                            d: "M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
                                        }
                                    }
                                }
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "System Health"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-green-600",
                                            "Healthy"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Admin actions
                div {
                    class: "mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2",
                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    svg {
                                        class: "h-6 w-6 text-gray-400",
                                        fill: "none",
                                        stroke: "currentColor",
                                        view_box: "0 0 24 24",
                                        "aria-hidden": "true",
                                        path {
                                            stroke_linecap: "round",
                                            stroke_linejoin: "round",
                                            stroke_width: "2",
                                            d: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                                        }
                                        path {
                                            stroke_linecap: "round",
                                            stroke_linejoin: "round",
                                            stroke_width: "2",
                                            d: "M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                        }
                                    }
                                }
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "System Settings"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-gray-900",
                                            "Configure system parameters"
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
                                    "Manage settings"
                                }
                            }
                        }
                    }

                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    svg {
                                        class: "h-6 w-6 text-gray-400",
                                        fill: "none",
                                        stroke: "currentColor",
                                        view_box: "0 0 24 24",
                                        "aria-hidden": "true",
                                        path {
                                            stroke_linecap: "round",
                                            stroke_linejoin: "round",
                                            stroke_width: "2",
                                            d: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                                        }
                                    }
                                }
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "Analytics Dashboard"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-gray-900",
                                            "View system metrics and reports"
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
                                    "View analytics"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}