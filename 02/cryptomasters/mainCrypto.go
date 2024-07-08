package cryptomasters

import (
	"fmt"
	"golearn/cryptomasters/api"
	"sync"
)

// main goroutine
func MainCrypto() {
	currencies := []string{"BTC", "ETH", "BCH"}
	var wg sync.WaitGroup
	for _, currency := range currencies {
		wg.Add(1)
		go func(currencyCode string) {
			getCurrencyCrypto(currencyCode)
			wg.Done()
		}(currency)
	}
	wg.Wait()
}

// new goroutine
func getCurrencyCrypto(currency string) {
	rate, err := api.GetRate(currency)
	if err == nil {
		fmt.Printf("The rate for %v is %.2f \n", rate.Currency, rate.Price)
	}
}
