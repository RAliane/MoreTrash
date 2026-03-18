use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

#[derive(Debug, Serialize, Deserialize, Clone)]
struct DemoItem {
    id: i32,
    name: String,
    description: String,
    category: String,
}

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: String,
    database: bool,
    directus: bool,
    vector_search: bool,
    demo_data: Vec<DemoItem>,
}

#[derive(Debug, Serialize)]
struct VectorSearchResult {
    id: i32,
    name: String,
    description: String,
    similarity: f32,
}

// Mock demo data
fn get_demo_items() -> Vec<DemoItem> {
    vec![
        DemoItem {
            id: 1,
            name: "Demo Item 1".to_string(),
            description: "First demonstration item with sample data".to_string(),
            category: "demo".to_string(),
        },
        DemoItem {
            id: 2,
            name: "Demo Item 2".to_string(),
            description: "Second demonstration item for testing".to_string(),
            category: "demo".to_string(),
        },
        DemoItem {
            id: 3,
            name: "Demo Item 3".to_string(),
            description: "Third demonstration item complete".to_string(),
            category: "demo".to_string(),
        },
    ]
}

fn create_http_response(status: &str, content_type: &str, body: &str) -> String {
    format!(
        "HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\n\r\n{}",
        status,
        content_type,
        body.len(),
        body
    )
}

fn parse_http_request(request: &str) -> (String, String, HashMap<String, String>) {
    let lines: Vec<&str> = request.lines().collect();
    if lines.is_empty() {
        return ("GET".to_string(), "/".to_string(), HashMap::new());
    }

    let first_line = lines[0];
    let parts: Vec<&str> = first_line.split_whitespace().collect();
    if parts.len() < 2 {
        return ("GET".to_string(), "/".to_string(), HashMap::new());
    }

    let method = parts[0].to_string();
    let path_query = parts[1];

    // Parse path and query
    let (path, query) = if let Some(pos) = path_query.find('?') {
        (path_query[..pos].to_string(), path_query[pos+1..].to_string())
    } else {
        (path_query.to_string(), "".to_string())
    };

    // Parse query parameters
    let mut params = HashMap::new();
    if !query.is_empty() {
        for pair in query.split('&') {
            if let Some(pos) = pair.find('=') {
                let key = pair[..pos].to_string();
                let value = pair[pos+1..].to_string();
                params.insert(key, value);
            }
        }
    }

    (method, path, params)
}

fn handle_request(request: &str) -> String {
    let (method, path, params) = parse_http_request(request);

    match (method.as_str(), path.as_str()) {
        ("GET", "/") => {
            let response = "🏠 Welcome to MysteryiousHounslow Dummy Demo!

This is a minimal demonstration of the hybrid kNN system.

Available endpoints:
- GET /health - System health check
- GET /items - List demo items
- GET /search?q=term&limit=5 - Search items
- POST /vector-search - Vector similarity search

Directus admin: http://localhost:8056
Database: postgres://localhost:5433/matchgorithm";
            create_http_response("200 OK", "text/plain", response)
        }

        ("GET", "/health") => {
            let demo_items = get_demo_items();
            let db_status = true; // Mock for demo
            let directus_status = true; // Mock for demo

            let health = HealthResponse {
                status: "ok".to_string(),
                database: db_status,
                directus: directus_status,
                vector_search: true,
                demo_data: demo_items,
            };

            let json = serde_json::to_string_pretty(&health).unwrap();
            create_http_response("200 OK", "application/json", &json)
        }

        ("GET", "/items") => {
            let items = get_demo_items();
            let json = serde_json::to_string_pretty(&items).unwrap();
            create_http_response("200 OK", "application/json", &json)
        }

        ("GET", "/search") => {
            let search_term = params.get("q").unwrap_or(&"".to_string()).to_lowercase();
            let limit: usize = params.get("limit")
                .and_then(|s| s.parse().ok())
                .unwrap_or(10);

            let all_items = get_demo_items();
            let filtered_items: Vec<DemoItem> = all_items
                .into_iter()
                .filter(|item|
                    item.name.to_lowercase().contains(&search_term) ||
                    item.description.to_lowercase().contains(&search_term)
                )
                .take(limit)
                .collect();

            let json = serde_json::to_string_pretty(&filtered_items).unwrap();
            create_http_response("200 OK", "application/json", &json)
        }

        ("POST", "/vector-search") => {
            // Mock vector search for POST requests
            let mock_results = vec![
                VectorSearchResult {
                    id: 1,
                    name: "Demo Item 1".to_string(),
                    description: "First demonstration item".to_string(),
                    similarity: 0.95,
                },
                VectorSearchResult {
                    id: 2,
                    name: "Demo Item 2".to_string(),
                    description: "Second demonstration item".to_string(),
                    similarity: 0.89,
                },
                VectorSearchResult {
                    id: 3,
                    name: "Demo Item 3".to_string(),
                    description: "Third demonstration item".to_string(),
                    similarity: 0.76,
                },
            ];

            let json = serde_json::to_string_pretty(&mock_results).unwrap();
            create_http_response("200 OK", "application/json", &json)
        }

        _ => {
            create_http_response("404 Not Found", "text/plain", "Not Found")
        }
    }
}

fn handle_connection(mut stream: TcpStream) {
    let mut buffer = [0; 1024];
    let bytes_read = stream.read(&mut buffer).unwrap_or(0);

    if bytes_read > 0 {
        let request = String::from_utf8_lossy(&buffer[..bytes_read]);
        let response = handle_request(&request);
        stream.write_all(response.as_bytes()).unwrap_or(());
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind("0.0.0.0:3000")?;
    println!("🚀 Dummy Demo Web Server listening on 0.0.0.0:3000");

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                thread::spawn(|| {
                    handle_connection(stream);
                });
            }
            Err(e) => {
                eprintln!("Connection failed: {}", e);
            }
        }
    }

    Ok(())
}