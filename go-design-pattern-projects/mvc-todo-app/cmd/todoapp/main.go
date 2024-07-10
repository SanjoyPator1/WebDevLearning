package main

import (
	"log"
	"mvc-todo-app/config"
	"mvc-todo-app/middlewares"
	"mvc-todo-app/routes"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Load environment variables
	if err := godotenv.Load("./config/.env"); err != nil {
		log.Fatalf("Error loading .env file: %v", err)
	}

	// Initialize configuration
	config.LoadConfig()

	// Initialize Gin router
	router := gin.Default()

	// Apply middlewares
    router.Use(middlewares.Logging())
    router.Use(middlewares.AuthRequired())

	// Register routes
	routes.RegisterRoutes(router)

	// Start the server
	log.Printf("Starting server on port %s...", config.Port)
	router.Run(":" + config.Port)
}
