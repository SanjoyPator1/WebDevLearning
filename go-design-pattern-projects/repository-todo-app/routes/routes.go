package routes

import (
	"repository-todo-app/controllers"
	"repository-todo-app/repositories"

	"github.com/gin-gonic/gin"
)

func RegisterRoutes(router *gin.Engine, repo repositories.TodoRepository) {
	todoController := controllers.NewTodoController(repo)

	router.GET("/todos", todoController.GetAllTodos)
	router.GET("/todos/:id", todoController.GetTodoByID)
	router.POST("/todos", todoController.CreateTodo)
	router.PUT("/todos/:id", todoController.UpdateTodoByID)
	router.DELETE("/todos/:id", todoController.DeleteTodoByID)
}
