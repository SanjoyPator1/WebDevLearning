package api_test

import (
	"golearn/cryptomasters/api"
	"testing"
)


func TestAPICall(t *testing.T){
	_, err := api.GetRate("")
	if err == nil {
        t.Error("Expected error, got nil")
    }
} 