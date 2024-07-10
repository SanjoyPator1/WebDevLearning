package main

import (
	"ddd-todo-app/internal/config"
	handler "ddd-todo-app/internal/todo"
	"ddd-todo-app/internal/todo/domain"
	"ddd-todo-app/internal/todo/middleware"
	"ddd-todo-app/internal/todo/service"
	"log"

	"github.com/gin-gonic/gin"
)

func main() {
	// Initialize configuration, MongoDB, and Redis
	config.Init()

	// Initialize MongoDB collection and repositories
	collection := config.MongoClient.Database(config.MongoDatabase).Collection(config.MongoCollection)
	todoRepo := domain.NewTodoRepository(collection)

	// Initialize services
	todoService := service.NewTodoService(todoRepo)
	handler.Init(todoService)

	// Initialize Gin router
	r := gin.Default()

	// Use AuthMiddleware for authentication
	r.Use(middleware.AuthMiddleware())

	// Setup routes
	handler.SetupRoutes(r)

	// Start server
	port := config.Port
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to run server: %v", err)
	}
}
