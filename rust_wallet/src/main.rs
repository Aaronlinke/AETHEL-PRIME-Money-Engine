use std::env;
use redis::{Client, Commands};

// Die Redis-URL ist fest auf localhost gesetzt
const REDIS_URL: &str = "redis://127.0.0.1/";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    
    // Prüfen, ob genügend Argumente vorhanden sind
    if args.len() < 3 {
        eprintln!("Usage: rust_wallet <token> <amount>");
        return Ok(());
    }
    
    let token = &args[1];
    let amount: f64 = args[2].parse()?;
    
    // Verbindung zu Redis herstellen
    let client = Client::open(REDIS_URL)?;
    let mut con = client.get_connection()?;
    
    // Wallet-Guthaben in Redis aktualisieren (persistent Claim)
    let key = format!("wallet:{}", token);
    let new_balance: f64 = con.incr(key, amount)?;
    
    // Ausgabe für Logging/Debugging
    println!("Rust Wallet updated: {} by {}. New balance: {}", token, amount, new_balance);
    
    Ok(())
}
