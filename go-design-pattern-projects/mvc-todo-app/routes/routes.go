package routes

import (
	"mvc-todo-app/controllers"

	"github.com/gin-gonic/gin"
)

func RegisterRoutes(router *gin.Engine) {
	router.GET("/todos", controllers.GetTodos)
	router.POST("/todos", controllers.CreateTodo)
	router.GET("/todos/:id", controllers.GetTodoByID)
	router.PUT("/todos/:id", controllers.UpdateTodoByID)
	router.DELETE("/todos/:id", controllers.DeleteTodoByID)
}
