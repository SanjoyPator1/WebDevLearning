package routes

import (
	"todo-app/controllers"

	"github.com/gin-gonic/gin"
)

// SetupRouter initializes the Gin router and defines routes for todo operations
func SetupRouter(todoController *controllers.TodoController) *gin.Engine {
	// Create a new default Gin router instance
	r := gin.Default()

	// Define HTTP routes for todo operations
	r.POST("/todos", todoController.CreateTask)       // HTTP POST to create a new todo
	r.GET("/todos", todoController.GetTasks)          // HTTP GET to fetch all todos
	r.GET("/todos/:id", todoController.GetTaskByID)   // HTTP GET to fetch a todo by ID
	r.PUT("/todos/:id", todoController.UpdateTask)    // HTTP PUT to update a todo by ID
	r.DELETE("/todos/:id", todoController.DeleteTask) // HTTP DELETE to delete a todo by ID

	return r
}
