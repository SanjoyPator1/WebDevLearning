package config

import (
	"log"
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

// Config holds configuration values loaded from .env file
type Config struct {
	MongoDBURI string
	RedisAddr  string
	RedisPass  string
	RedisDB    int
	Port       string
}

// LoadConfig loads configuration values from .env file
func LoadConfig() *Config {
	// Load environment variables from .env file
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found")
	}

	// Convert Redis DB from string to integer
	redisDB, err := strconv.Atoi(getEnv("REDIS_DB", "0"))
	if err != nil {
		log.Fatalf("Invalid REDIS_DB: %v", err)
	}

	// Return a Config struct with the loaded values
	return &Config{
		MongoDBURI: getEnv("MONGODB_URI", "mongodb://localhost:27017/todo-app"),
		RedisAddr:  getEnv("REDIS_ADDR", "localhost:6379"),
		RedisPass:  getEnv("REDIS_PASSWORD", ""),
		RedisDB:    redisDB,
		Port:       getEnv("PORT", "8080"),
	}
}

// getEnv fetches environment variables with a default fallback
func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
