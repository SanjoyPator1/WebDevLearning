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
	Ctx         = context.TODO()
	RedisClient *redis.Client
	Port        string
)

func LoadConfig() {
	if err := godotenv.Load("config/.env"); err != nil {
		log.Println("No .env file found")
	}

	mongoURI := os.Getenv("MONGODB_URI")
	redisAddr := os.Getenv("REDIS_ADDR")
	Port = os.Getenv("PORT")
	if Port == "" {
		Port = "8080" // Default port if not specified
	}

	// Initialize MongoDB client
	var err error
	MongoClient, err = mongo.Connect(Ctx, options.Client().ApplyURI(mongoURI))
	if err != nil {
		log.Fatal(err)
	}

	// Initialize Redis client
	RedisClient = redis.NewClient(&redis.Options{
		Addr: redisAddr,
	})
}
