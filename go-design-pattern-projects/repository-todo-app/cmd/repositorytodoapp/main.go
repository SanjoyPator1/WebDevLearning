package main

import (
	"log"
	"os"
	"repository-todo-app/config"
	"repository-todo-app/repositories"
	"repository-todo-app/routes"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Load environment variables
	loadEnv()

	// Initialize configuration and dependencies
	initialize()

	// Initialize Gin router and register routes
	router := gin.Default()
	todoRepo, err := repositories.NewTodoRepository()
	if err != nil {
		log.Fatalf("Error initializing repository: %v", err)
	}
	routes.RegisterRoutes(router, todoRepo)

	// Start the server
	startServer(router)
}

func loadEnv() {
	if err := godotenv.Load("./config/.env"); err != nil {
		log.Fatalf("Error loading .env file: %v", err)
	}
}

func initialize() {
	config.LoadConfig()
	config.InitMongoDB()
	config.InitRedis()
}

func startServer(router *gin.Engine) {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080" // Default port if not specified
	}
	router.Run(":" + port)
}
