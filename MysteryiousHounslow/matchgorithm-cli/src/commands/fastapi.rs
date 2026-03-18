use clap::Subcommand;
use super::*;

#[derive(Subcommand)]
pub enum FastapiCommands {
    /// Call FastAPI service functions
    Call {
        #[arg(short, long)]
        endpoint: String,
        #[arg(short, long)]
        method: Option<String>,
        #[arg(short, long)]
        data: Option<String>,
    },
    /// List available FastAPI endpoints
    List,
    /// Test FastAPI health
    Health,
    /// Call kNN service
    Knn {
        #[arg(short, long)]
        vector: Option<String>,
        #[arg(short, long)]
        max_results: Option<usize>,
    },
}

pub async fn handle_command(cmd: FastapiCommands) -> Result<(), CliError> {
    let config = Config::load()?;
    let client = ApiClient::new(config.fastapi_url, config.auth_token, config.timeout);

    match cmd {
        FastapiCommands::Call { endpoint, method, data } => {
            call_endpoint(&client, &endpoint, method.as_deref(), data.as_deref()).await
        }
        FastapiCommands::List => list_endpoints(&client).await,
        FastapiCommands::Health => check_health(&client).await,
        FastapiCommands::Knn { vector, max_results } => {
            call_knn_service(&client, vector, max_results).await
        }
    }
}

pub async fn call_endpoint(
    client: &ApiClient,
    endpoint: &str,
    method: Option<&str>,
    data: Option<&str>
) -> Result<(), CliError> {
    let method = method.unwrap_or("GET").to_uppercase();
    let json_data = data.map(|d| serde_json::from_str(d).unwrap_or_else(|_| serde_json::json!({})));

    let result = match method.as_str() {
        "GET" => client.get(endpoint).await?,
        "POST" => client.post(endpoint, json_data.as_ref().unwrap_or(&serde_json::json!({}))).await?,
        "PUT" => client.put(endpoint, json_data.as_ref().unwrap_or(&serde_json::json!({}))).await?,
        "DELETE" => client.delete(endpoint).await?,
        _ => return Err(CliError::ApiError(format!("Unsupported method: {}", method))),
    };

    println!("{}", result);
    Ok(())
}

pub async fn list_endpoints(client: &ApiClient) -> Result<(), CliError> {
    // In a real implementation, this would call a /docs or /openapi endpoint
    println!("📋 Available FastAPI Endpoints:");
    println!("/api/v1/health - GET - Health check");
    println!("/api/v1/optimize - POST - Optimization pipeline");
    println!("/api/v1/knn - POST - kNN service");
    println!("/api/v1/hybrid_knn - POST - Hybrid kNN service");
    println!("/api/v1/users - GET/POST - User management");
    println!("/api/v1/matches - GET - Match results");

    Ok(())
}

pub async fn check_health(client: &ApiClient) -> Result<(), CliError> {
    let result = client.get("api/v1/health").await?;
    println!("{}", result);
    Ok(())
}

pub async fn call_knn_service(
    client: &ApiClient,
    vector: Option<String>,
    max_results: Option<usize>
) -> Result<(), CliError> {
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

    let pb = ProgressBar::new_spinner();
    pb.set_message("Calling kNN service...");

    let data = serde_json::json!({
        "query_vector": vector,
        "max_results": max_results
    });

    let result = client.post("api/v1/knn", &data).await?;
    pb.finish_with_message("✅ kNN service response:");

    println!("{}", result);
    Ok(())
}