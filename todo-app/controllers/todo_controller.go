package controllers

import (
	"net/http"
	"todo-app/services"

	"github.com/gin-gonic/gin"
)

// TodoController handles HTTP requests for todo tasks
type TodoController struct {
	service *services.TodoService
}

// NewTodoController creates a new TodoController instance with the given TodoService
func NewTodoController(service *services.TodoService) *TodoController {
	return &TodoController{service: service}
}

// CreateTask handles HTTP POST requests to create a new todo task
func (ctrl *TodoController) CreateTask(c *gin.Context) {
	// Define a variable to hold the input data for creating a task
	var task services.CreateTaskInput

	// Bind the JSON payload from the request body to the CreateTaskInput struct
	if err := c.ShouldBindJSON(&task); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Call the service to create the task, passing the Gin context and task input
	if err := ctrl.service.CreateTask(c, task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Respond with HTTP status 201 indicating successful creation
	c.Status(http.StatusCreated)
}

// GetTasks handles HTTP GET requests to fetch all todo tasks
func (ctrl *TodoController) GetTasks(c *gin.Context) {
	// Call the service to get all tasks, passing the Gin context
	tasks, err := ctrl.service.GetTasks(c)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Respond with the fetched tasks in JSON format with HTTP status 200
	c.JSON(http.StatusOK, tasks)
}

// GetTaskByID handles HTTP GET requests to fetch a specific todo task by its ID
func (ctrl *TodoController) GetTaskByID(c *gin.Context) {
	// Extract the task ID from the URL parameter
	id := c.Param("id")

	// Call the service to get the task by ID, passing the Gin context and task ID
	task, err := ctrl.service.GetTaskByID(c, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Respond with the fetched task in JSON format with HTTP status 200
	c.JSON(http.StatusOK, task)
}

// UpdateTask handles HTTP PUT requests to update a todo task by its ID
func (ctrl *TodoController) UpdateTask(c *gin.Context) {
	// Extract the task ID from the URL parameter
	id := c.Param("id")

	// Define a variable to hold the input data for updating a task
	var task services.UpdateTaskInput

	// Bind the JSON payload from the request body to the UpdateTaskInput struct
	if err := c.ShouldBindJSON(&task); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Call the service to update the task, passing the Gin context, task ID, and task input
	if err := ctrl.service.UpdateTask(c, id, task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Respond with HTTP status 200 indicating successful update
	c.Status(http.StatusOK)
}

// DeleteTask handles HTTP DELETE requests to delete a todo task by its ID
func (ctrl *TodoController) DeleteTask(c *gin.Context) {
	// Extract the task ID from the URL parameter
	id := c.Param("id")

	// Call the service to delete the task, passing the Gin context and task ID
	if err := ctrl.service.DeleteTask(c, id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Respond with HTTP status 204 indicating successful deletion with no content returned
	c.Status(http.StatusNoContent)
}