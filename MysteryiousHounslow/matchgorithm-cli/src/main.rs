// kNN operations
async fn test_knn(vector: Vec<f32>, max_results: usize) -> Result<()> {
    println!("🧮 Testing hybrid kNN endpoint...");

    // Validate input
    if vector.len() != 384 {
        return Err(anyhow::anyhow!("Vector must have 384 dimensions, got {}", vector.len()));
    }

    // Call FastAPI service
    let client = Client::new();
    let response = client
        .post("http://localhost:8001/api/v1/hybrid_knn")
        .json(&serde_json::json!({
            "query_vector": vector,
            "max_results": max_results
        }))
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(anyhow::anyhow!("FastAPI error: {}", response.text().await?));
    }

    let results: serde_json::Value = response.json().await?;
    println!("{}", serde_json::to_string_pretty(&results)?);

    Ok(())
}

async fn benchmark_knn(test_vectors: usize, probes: usize) -> Result<()> {
    println!("🚀 Benchmarking kNN performance...");

    // Call FastAPI benchmark endpoint
    let client = Client::new();
    let response = client
        .post("http://localhost:8001/api/v1/knn/benchmark")
        .json(&serde_json::json!({
            "test_vectors": test_vectors,
            "probes": probes
        }))
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(anyhow::anyhow!("FastAPI benchmark error: {}", response.text().await?));
    }

    let results: serde_json::Value = response.json().await?;
    println!("{}", serde_json::to_string_pretty(&results)?);

    Ok(())
}

async fn rebuild_knn() -> Result<()> {
    println!("🔄 Rebuilding kNN indices...");

    // Call FastAPI rebuild endpoint
    let client = Client::new();
    let response = client
        .post("http://localhost:8001/api/v1/knn/rebuild")
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(anyhow::anyhow!("FastAPI rebuild error: {}", response.text().await?));
    }

    let results: serde_json::Value = response.json().await?;
    println!("{}", serde_json::to_string_pretty(&results)?);

    Ok(())
}

async fn check_knn_health() -> Result<()> {
    println!("🏥 kNN Health Status:");

    // Check FastAPI service
    let client = Client::new();
    let api_health = client
        .get("http://localhost:8001/health")
        .send()
        .await?
        .status()
        .is_success();

    // Check kNN specific health
    let knn_health = client
        .get("http://localhost:8001/api/v1/knn/health")
        .send()
        .await?
        .status()
        .is_success();

    println!("- FastAPI: {}", if api_health { "✅ Healthy" } else { "❌ Unhealthy" });
    println!("- kNN Service: {}", if knn_health { "✅ Healthy" } else { "❌ Unhealthy" });
    println!("- Overall: {}", if api_health && knn_health { "✅ All Systems Operational" } else { "❌ Issues Detected" });

    Ok(())
}

// FastAPI operations
async fn call_fastapi_endpoint(endpoint: &str, method: Option<&str>, data: Option<&str>) -> Result<()> {
    let method = method.unwrap_or("GET").to_uppercase();
    let client = Client::new();

    let url = format!("http://localhost:8001{}", endpoint);

    let response = match method.as_str() {
        "GET" => client.get(&url).send().await?,
        "POST" => client.post(&url).json(&data.map(|d| serde_json::from_str(d).unwrap_or_else(|_| serde_json::json!({})))).send().await?,
        "PUT" => client.put(&url).json(&data.map(|d| serde_json::from_str(d).unwrap_or_else(|_| serde_json::json!({})))).send().await?,
        "DELETE" => client.delete(&url).send().await?,
        _ => return Err(anyhow::anyhow!("Unsupported method: {}", method)),
    };

    if !response.status().is_success() {
        return Err(anyhow::anyhow!("API error {}: {}",
            response.status(),
            response.text().await?
        ));
    }

    println!("{}", response.text().await?);
    Ok(())
}

async fn list_fastapi_endpoints() -> Result<()> {
    println!("📋 Available FastAPI Endpoints:");
    println!("/api/v1/health - GET - Health check");
    println!("/api/v1/optimize - POST - Optimization pipeline");
    println!("/api/v1/knn - POST - kNN service");
    println!("/api/v1/hybrid_knn - POST - Hybrid kNN service");
    println!("/api/v1/users - GET/POST - User management");
    println!("/api/v1/matches - GET - Match results");

    Ok(())
}

async fn check_fastapi_health() -> Result<()> {
    let client = Client::new();
    let response = client
        .get("http://localhost:8001/health")
        .send()
        .await?;

    let status = response.status();
    let body = response.text().await?;

    println!("FastAPI Health Status:");
    println!("Status: {}", status);
    println!("Response: {}", body);

    if !status.is_success() {
        return Err(anyhow::anyhow!("FastAPI health check failed"));
    }

    Ok(())
}

async fn call_fastapi_knn(vector: Option<&str>, max_results: Option<usize>) -> Result<()> {
    let vector = vector.unwrap_or_else(|| {
        Input::new()
            .with_prompt("Enter query vector (comma-separated)")
            .default("[0.1,0.2,0.3,0.4,0.5]".to_string())
            .interact()
            .unwrap()
    });

    let max_results = max_results.unwrap_or_else(|| {
        Input::new()
            .with_prompt("Max results")
            .default(10)
            .interact()
            .unwrap()
    });

    println!("🔗 Calling FastAPI kNN service...");
    println!("Vector: {}", vector);
    println!("Max Results: {}", max_results);

    let client = Client::new();
    let response = client
        .post("http://localhost:8001/api/v1/knn")
        .json(&serde_json::json!({
            "query_vector": vector,
            "max_results": max_results
        }))
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(anyhow::anyhow!("kNN service error: {}", response.text().await?));
    }

    let results: serde_json::Value = response.json().await?;
    println!("{}", serde_json::to_string_pretty(&results)?);

    Ok(())
}