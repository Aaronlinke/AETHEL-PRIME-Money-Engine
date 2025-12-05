package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
	"math/rand"
)

// Trade-Struktur, die als JSON ausgegeben wird
type Trade struct {
	Token     string  `json:"token"`
	Type      string  `json:"type"`
	Amount    float64 `json:"amount"`
	Price     float64 `json:"price"`
	Timestamp int64   `json:"timestamp"`
	ProfitUSD float64 `json:"profit_usd"` // Neuer Feld für den Gewinn
}

// BinancePriceResponse Struktur für die API-Antwort
type BinancePriceResponse struct {
	Symbol string `json:"symbol"`
	Price  string `json:"price"`
}

// getPrice ruft den aktuellen Preis für ein Symbol von der Binance API ab
func getPrice(symbol string) (float64, error) {
	url := fmt.Sprintf("https://data-api.binance.vision/api/v3/ticker/price?symbol=%s", symbol)
	
	resp, err := http.Get(url)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, err
	}

	var priceResponse BinancePriceResponse
	err = json.Unmarshal(body, &priceResponse)
	if err != nil {
		return 0, err
	}

	var price float64
	fmt.Sscanf(priceResponse.Price, "%f", &price)
	return price, nil
}

func main() {
	rand.Seed(time.Now().UnixNano())
	
	// Nur in 30% der Fälle einen Trade ausführen, um die Simulation realistischer zu machen
	if rand.Float64() > 0.3 {
		fmt.Println("[]") // Kein Trade
		return
	}

	// Wir simulieren eine Arbitrage-Gelegenheit zwischen zwei fiktiven Börsen A und B
	// und nutzen den echten Binance-Preis als Basis.
	
	// 1. Echten Preis abrufen
	symbol := "BTCUSDT"
	basePrice, err := getPrice(symbol)
	if err != nil {
		// Bei Fehler leeres Array zurückgeben
		fmt.Println("[]")
		return
	}

	// 2. Arbitrage-Logik simulieren
	// Börse A: Kaufpreis (etwas niedriger als der Basispreis)
	buyPriceA := basePrice * (1.0 - (rand.Float64() * 0.0001 + 0.00005)) // 0.005% bis 0.01% unter Basis
	
	// Börse B: Verkaufspreis (etwas höher als der Basispreis)
	sellPriceB := basePrice * (1.0 + (rand.Float64() * 0.0001 + 0.00005)) // 0.005% bis 0.01% über Basis
	
	// Gewinnberechnung
	amount := 0.01 // Feste Menge für den Trade (0.01 BTC)
	profit := (sellPriceB - buyPriceA) * amount
	
	// Nur ausführen, wenn der Gewinn positiv ist (was bei dieser Simulation immer der Fall ist)
	if profit > 0 {
		trade := Trade{
			Token:     "BTC",
			Type:      "Arbitrage",
			Amount:    amount,
			Price:     buyPriceA, // Wir loggen den Kaufpreis
			Timestamp: time.Now().Unix(),
			ProfitUSD: profit,
		}
		
		trades := []Trade{trade}
		output, _ := json.Marshal(trades)
		fmt.Println(string(output))
	} else {
		fmt.Println("[]")
	}
}
