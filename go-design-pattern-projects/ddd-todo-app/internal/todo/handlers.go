// internal/todo/handler/handlers.go

package handler

import (
	"ddd-todo-app/internal/todo/domain"
	"ddd-todo-app/internal/todo/service"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

// Define a global variable for the TodoService
var todoService service.TodoService

// Init initializes the service with a given repository
func Init(service service.TodoService) {
	todoService = service
}

// GetTodosHandler handles GET requests to fetch all todos
func GetTodosHandler(c *gin.Context) {
	todos, err := todoService.GetAll()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch todos"})
		return
	}
	c.JSON(http.StatusOK, todos)
}

// CreateTodoHandler handles POST requests to create a new todo
func CreateTodoHandler(c *gin.Context) {
	var todo domain.Todo
	fmt.Printf("handlers start create todo: %v\n", todo)
	if err := c.ShouldBindJSON(&todo); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid todo data"})
		return
	}
	if err := todoService.Create(&todo); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create todo"})
		return
	}
	fmt.Printf("handlers finish create todo: %v\n", todo)
	c.JSON(http.StatusCreated, todo)
}

// GetTodoHandler handles GET requests to fetch a single todo by ID
func GetTodoHandler(c *gin.Context) {
	id := c.Param("id")
	objectID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid todo ID"})
		return
	}

	todo, err := todoService.Get(objectID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Todo not found"})
		return
	}
	c.JSON(http.StatusOK, todo)
}

// UpdateTodoHandler handles PUT requests to update an existing todo by ID
func UpdateTodoHandler(c *gin.Context) {
	id := c.Param("id")
	objectID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid todo ID"})
		return
	}

	var todo domain.Todo
	if err := c.ShouldBindJSON(&todo); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid todo data"})
		return
	}
	todo.ID = objectID // Set ID from path parameter in todo struct

	if err := todoService.Update(&todo); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update todo"})
		return
	}
	c.JSON(http.StatusOK, todo)
}

// DeleteTodoHandler handles DELETE requests to delete a todo by ID
func DeleteTodoHandler(c *gin.Context) {
	id := c.Param("id")
	objectID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid todo ID"})
		return
	}

	if err := todoService.Delete(objectID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete todo"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Todo deleted successfully"})
}

// SetupRoutes initializes routes and middleware for the application
func SetupRoutes(r *gin.Engine) {
	// Define routes
	todoGroup := r.Group("/todos")
	{
		todoGroup.GET("/", GetTodosHandler)         // GET /todos
		todoGroup.POST("/", CreateTodoHandler)      // POST /todos
		todoGroup.GET("/:id", GetTodoHandler)       // GET /todos/:id
		todoGroup.PUT("/:id", UpdateTodoHandler)    // PUT /todos/:id
		todoGroup.DELETE("/:id", DeleteTodoHandler) // DELETE /todos/:id
	}
}
