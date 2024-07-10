// config/config.go
package config

import (
	"context"
	"log"
	"os"

	"github.com/go-redis/redis/v8"
	"github.com/joho/godotenv"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

var (
	MongoClient *mongo.Client
	RedisClient *redis.Client
)

// LoadConfig loads environment variables from the .env file.
func LoadConfig() {
	err := godotenv.Load("./config/.env")
	if err != nil {
		log.Fatalf("Error loading .env file: %v", err)
	}
}

// InitMongoDB initializes the MongoDB client.
func InitMongoDB() {
	uri := os.Getenv("MONGODB_URI")
	if uri == "" {
		log.Fatal("MONGODB_URI not found in .env")
	}

	clientOptions := options.Client().ApplyURI(uri)
	client, err := mongo.Connect(context.Background(), clientOptions)
	if err != nil {
		log.Fatalf("Error connecting to MongoDB: %v", err)
	}

	err = client.Ping(context.Background(), nil)
	if err != nil {
		log.Fatalf("Error pinging MongoDB: %v", err)
	}

	MongoClient = client
}

// InitRedis initializes the Redis client.
func InitRedis() {
	redisURI := os.Getenv("REDIS_ADDR")
	if redisURI == "" {
		log.Fatal("REDIS_ADDR not found in .env")
	}

	RedisClient = redis.NewClient(&redis.Options{
		Addr: redisURI,
	})

	_, err := RedisClient.Ping(context.Background()).Result()
	if err != nil {
		log.Fatalf("Error connecting to Redis: %v", err)
	}
}
