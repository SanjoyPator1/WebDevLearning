// utils/utils.go
package utils

import (
	"crypto/rand"
	"encoding/hex"
)

func GenerateID() string {
	id := make([]byte, 12)
	_, err := rand.Read(id)
	if err != nil {
		panic(err)
	}
	return hex.EncodeToString(id)
}
