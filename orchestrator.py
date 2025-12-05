import asyncio, aiohttp, json, subprocess, websockets, redis
from datetime import datetime

# Konfiguration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
WEBSOCKET_PORT = 8765
clients = set()

async def broadcast(message):
    """Sendet eine Nachricht an alle verbundenen WebSocket-Clients."""
    if clients:
        # Erstellt eine Liste von Sende-Tasks und ignoriert Fehler (z.B. getrennte Clients)
        await asyncio.wait([client.send(message) for client in clients], return_when=asyncio.FIRST_EXCEPTION)

class FreeMoneyScanner:
    """Simuliert das Scannen nach freien Einnahmequellen."""
    def __init__(self, sources):
        self.sources = sources

    async def scan(self):
        """Führt asynchrone Scans durch und gibt eine Liste von Items zurück."""
        results = []
        # Die API ist fake, daher wird ein Dummy-Ergebnis zurückgegeben, um den Flow zu testen
        dummy_data = [
            {"token": "BTC", "amount": 0.00001},
            {"token": "ETH", "amount": 0.0001},
        ]
        
        # Simuliere API-Aufrufe
        await asyncio.sleep(0.5)
        
        # In einer echten Implementierung würde hier der aiohttp-Code stehen:
        # async with aiohttp.ClientSession() as session:
        #     for url in self.sources:
        #         try:
        #             async with session.get(url) as resp:
        #                 data = await resp.json()
        #                 results.extend(data.get('airdrops', []))
        #         except:
        #             continue
        # return results
        
        return dummy_data

    async def claim(self, item):
        """Führt den Claim-Prozess durch und triggert Rust Wallet Update."""
        token = item['token']
        amount = item['amount']
        
        # 1. Rust Wallet Sync (Simuliert)
        # In einer echten Umgebung müsste das Rust-Programm die Redis-Datenbank aktualisieren.
        # Da wir hier Redis direkt im Python-Orchestrator aktualisieren,
        # simulieren wir den Aufruf und das Rust-Programm wird nur zur Demonstration der Multi-Language-Architektur verwendet.
        try:
            subprocess.run(["./rust_wallet/target/release/rust_wallet", token, str(amount)], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Rust Wallet Error: {e.stderr.decode()}")
            
        # 2. Update Redis Bucket
        REDIS.incrbyfloat(f"wallet:{token}", amount)
        
        # 3. Broadcast an Dashboard
        current_balance = REDIS.get(f"wallet:{token}")
        message = json.dumps({
            "type": "CLAIM",
            "timestamp": datetime.utcnow().isoformat(),
            "token": token,
            "amount": amount,
            "new_balance": current_balance
        })
        await broadcast(f"CLAIM: {amount} {token}. New Balance: {current_balance}")
        
        return message

async def run_go_arbitrage():
    """Triggert den Go Arbitrage Layer."""
    try:
        result = subprocess.run(["go", "run", "arbitrage.go"], check=True, capture_output=True)
        # Beispiel: parse Trades
        trades = json.loads(result.stdout.decode() or "[]")
        for trade in trades:
            # 1. Update Redis Bucket
            key = f"trade:{trade['token']}:{trade['timestamp']}"
            REDIS.set(key, json.dumps(trade))
            
            # 2. Broadcast an Dashboard
            profit = trade.get('profit_usd', 0.0)
            
            message = json.dumps({
                "type": "TRADE",
                "timestamp": datetime.utcnow().isoformat(),
                "trade": trade
            })
            await broadcast(f"TRADE: {trade['type']} {trade['amount']} {trade['token']} at {trade['price']}. PROFIT: ${profit:.2f}")   
    except subprocess.CalledProcessError as e:
        await broadcast(f"Arbitrage Error: {e.stderr.decode()}")
    except json.JSONDecodeError:
        await broadcast(f"Arbitrage Output Error: {result.stdout.decode().strip()}")

async def run_node_content():
    """Triggert den Node.js Content Layer."""
    try:
        result = subprocess.run(["node", "content_engine.js"], check=True, capture_output=True)
        
        # Node-Programm gibt JSON des erstellten NFT aus
        nft = json.loads(result.stdout.decode().strip() or "{}")
        
        # 1. Update Redis Bucket
        key = f"nft:{datetime.utcnow().timestamp()}"
        REDIS.set(key, json.dumps(nft))
        
        # 2. Broadcast an Dashboard
        message = json.dumps({
            "type": "NFT",
            "timestamp": datetime.utcnow().isoformat(),
            "nft": nft
        })
        await broadcast(f"NFT Created: {nft.get('name')} with earnings {nft.get('earnings')}")
        
    except subprocess.CalledProcessError as e:
        await broadcast(f"NFT Content Error: {e.stderr.decode()}")
    except json.JSONDecodeError:
        await broadcast(f"NFT Content Output Error: {result.stdout.decode().strip()}")

async def websocket_handler(websocket, path):
    """Behandelt neue WebSocket-Verbindungen."""
    clients.add(websocket)
    try:
        # Sende initialen Wallet-Status
        wallet_keys = REDIS.keys("wallet:*")
        initial_status = {
            "type": "INIT_WALLET",
            "balances": {key.split(':')[1]: REDIS.get(key) for key in wallet_keys}
        }
        await websocket.send(json.dumps(initial_status))
        
        async for message in websocket:
            # Hier könnte man Befehle vom Frontend verarbeiten
            pass
    finally:
        clients.remove(websocket)

async def main():
    """Haupt-Orchestrierungs-Loop."""
    scanner = FreeMoneyScanner(['https://fake-api.io/airdrops'])
    
    # Starte WebSocket-Server
    ws_server = await websockets.serve(websocket_handler, "0.0.0.0", WEBSOCKET_PORT)
    print(f"WebSocket Server gestartet auf ws://0.0.0.0:{WEBSOCKET_PORT}")
    
    # Haupt-Loop
    while True:
        print(f"--- Starte Scan-Zyklus um {datetime.now().isoformat()} ---")
        items = await scanner.scan()
        
        if items:
            # Führe Claims parallel aus
            claim_tasks = [scanner.claim(item) for item in items]
            await asyncio.gather(*claim_tasks)
            
            # Führe Arbitrage und Content-Generierung parallel aus
            await asyncio.gather(run_go_arbitrage(), run_node_content())
            
        print("--- Zyklus beendet. Warte 10 Sekunden. ---")
        await asyncio.sleep(10)

if __name__ == "__main__":
    # Stelle sicher, dass Redis läuft und initialisiere ggf. die Wallet
    if not REDIS.ping():
        print("FEHLER: Redis-Server nicht erreichbar.")
        exit(1)
        
    # Erstelle das Verzeichnis für NFTs
    subprocess.run(["mkdir", "-p", "nfts"])
    
    # Rust-Projekt wurde bereits vorbereitet und kompiliert.
    
    # Starte den Hauptprozess
    asyncio.run(main())
