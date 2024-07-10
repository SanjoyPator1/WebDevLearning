package utils

import (
	"crypto/rand"
	"encoding/base64"
	"log"
)

// GenerateRandomString creates a random string of a specified length
func GenerateRandomString(n int) string {
	b := make([]byte, n)
	_, err := rand.Read(b)
	if err != nil {
		log.Fatal(err)
	}
	return base64.URLEncoding.EncodeToString(b)
}
