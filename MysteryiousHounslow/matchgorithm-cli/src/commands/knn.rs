use clap::Subcommand;
use super::*;

#[derive(Subcommand)]
pub enum KnnCommands {
    /// Test hybrid kNN endpoint
    Test {
        #[arg(short, long)]
        vector: Vec<f32>,
        #[arg(short, long, default_value = "10")]
        max_results: usize,
    },
    /// Benchmark kNN performance
    Benchmark {
        #[arg(short, long, default_value = "1000")]
        test_vectors: usize,
        #[arg(short, long, default_value = "10")]
        probes: usize,
    },
    /// Rebuild kNN indices
    Rebuild,
    /// Check kNN health
    Health,
}

pub async fn handle_command(cmd: KnnCommands) -> Result<(), CliError> {
    match cmd {
        KnnCommands::Test { vector, max_results } => test(vector, max_results).await,
        KnnCommands::Benchmark { test_vectors, probes } => benchmark(test_vectors, probes).await,
        KnnCommands::Rebuild => rebuild().await,
        KnnCommands::Health => health().await,
    }
}

pub async fn test(vector: Vec<f32>, max_results: usize) -> Result<(), CliError> {
    // Validate input
    if vector.len() != 384 {
        return Err(CliError::ValidationError(
            format!("Vector must have 384 dimensions, got {}", vector.len())
        ));
    }

    // Call FastAPI service
    let client = reqwest::Client::new();
    let response = client
        .post("http://localhost:8001/api/v1/hybrid_knn")
        .json(&serde_json::json!({
            "query_vector": vector,
            "max_results": max_results
        }))
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(CliError::ApiError(
            format!("FastAPI error: {}", response.text().await?)
        ));
    }

    let results: serde_json::Value = response.json().await?;
    println!("{}", serde_json::to_string_pretty(&results)?);

    Ok(())
}

pub async fn benchmark(test_vectors: usize, probes: usize) -> Result<(), CliError> {
    println!("🚀 Benchmarking kNN performance...");

    // Generate test vectors
    let test_vector: Vec<f32> = (0..384).map(|_| rand::random()).collect();

    // Call FastAPI benchmark endpoint (assuming it exists)
    let client = reqwest::Client::new();
    let response = client
        .post("http://localhost:8001/api/v1/knn/benchmark")
        .json(&serde_json::json!({
            "test_vectors": test_vectors,
            "probes": probes,
            "query_vector": test_vector
        }))
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(CliError::ApiError(
            format!("FastAPI benchmark error: {}", response.text().await?)
        ));
    }

    let results: serde_json::Value = response.json().await?;
    println!("{}", serde_json::to_string_pretty(&results)?);

    Ok(())
}

pub async fn rebuild() -> Result<(), CliError> {
    println!("🔄 Rebuilding kNN indices...");

    // Call FastAPI rebuild endpoint
    let client = reqwest::Client::new();
    let response = client
        .post("http://localhost:8001/api/v1/knn/rebuild")
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(CliError::ApiError(
            format!("FastAPI rebuild error: {}", response.text().await?)
        ));
    }

    let results: serde_json::Value = response.json().await?;
    println!("{}", serde_json::to_string_pretty(&results)?);

    Ok(())
}

pub async fn health() -> Result<(), CliError> {
    println!("🏥 kNN Health Status:");

    // Check FastAPI service
    let client = reqwest::Client::new();
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