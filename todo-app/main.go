package main

import (
	"context"
	"log"
	"todo-app/config"
	"todo-app/controllers"
	"todo-app/repositories"
	"todo-app/routes"
	"todo-app/services"

	"github.com/go-redis/redis/v8"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

func main() {
	// Load configuration from .env file
	cfg := config.LoadConfig()

	// Connect to MongoDB
	mongoClient, err := mongo.Connect(context.TODO(), options.Client().ApplyURI(cfg.MongoDBURI))
	if err != nil {
		log.Fatal(err)
	}
	defer mongoClient.Disconnect(context.TODO())

	// Connect to Redis
	redisClient := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisAddr, // Redis server address
		Password: cfg.RedisPass, // Redis password
		DB:       cfg.RedisDB,   // Redis database number
	})

	// Initialize MongoDB repository
	todoRepository := repositories.NewTodoRepository(mongoClient)

	// Initialize TodoService with MongoDB repository and Redis client
	todoService := services.NewTodoService(todoRepository, redisClient)

	// Initialize TodoController with TodoService
	todoController := controllers.NewTodoController(todoService)

	// Setup Gin router with TodoController
	r := routes.SetupRouter(todoController)

	// Start the HTTP server using configured port
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal(err)
	}
}
