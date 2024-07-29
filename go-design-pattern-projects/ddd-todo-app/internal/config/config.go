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
	MongoClient     *mongo.Client
	RedisClient     *redis.Client
	Port            string
	MongoDatabase   string
	MongoCollection string
)

// LoadConfig loads environment variables from the .env file.
func LoadConfig() {
	err := godotenv.Load(".env")
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

// Init initializes the configuration, MongoDB, and Redis.
func Init() {
	LoadConfig()
	InitMongoDB()
	InitRedis()

	Port = os.Getenv("PORT")
	if Port == "" {
		log.Fatal("PORT not found in .env")
	}

	MongoDatabase = os.Getenv("MONGODB_DATABASE")
	if MongoDatabase == "" {
		log.Fatal("MONGODB_DATABASE not found in .env")
	}

	MongoCollection = os.Getenv("MONGODB_COLLECTION")
	if MongoCollection == "" {
		log.Fatal("MONGODB_COLLECTION not found in .env")
	}
}
