package controllers

import (
	"net/http"
	"repository-todo-app/models"
	"repository-todo-app/repositories"

	"github.com/gin-gonic/gin"
)

type TodoController interface {
	GetAllTodos(ctx *gin.Context)
	GetTodoByID(ctx *gin.Context)
	CreateTodo(ctx *gin.Context)
	UpdateTodoByID(ctx *gin.Context)
	DeleteTodoByID(ctx *gin.Context)
}

type todoController struct {
	repo repositories.TodoRepository
}

func NewTodoController(repo repositories.TodoRepository) TodoController {
	return &todoController{
		repo: repo,
	}
}

func (controller *todoController) GetAllTodos(ctx *gin.Context) {
	todos, err := controller.repo.GetAll()
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch todos"})
		return
	}
	ctx.JSON(http.StatusOK, todos)
}

func (controller *todoController) GetTodoByID(ctx *gin.Context) {
	id := ctx.Param("id")
	todo, err := controller.repo.GetByID(id)
	if err != nil {
		ctx.JSON(http.StatusNotFound, gin.H{"error": "Todo not found"})
		return
	}
	ctx.JSON(http.StatusOK, todo)
}

func (controller *todoController) CreateTodo(ctx *gin.Context) {
	var todo models.Todo
	if err := ctx.ShouldBindJSON(&todo); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
		return
	}

	err := controller.repo.Create(&todo)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create todo"})
		return
	}

	ctx.JSON(http.StatusCreated, todo)
}

func (controller *todoController) UpdateTodoByID(ctx *gin.Context) {
	id := ctx.Param("id")
	var todo models.Todo
	if err := ctx.ShouldBindJSON(&todo); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
		return
	}

	err := controller.repo.UpdateByID(id, &todo)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update todo"})
		return
	}

	updatedTodo, _ := controller.repo.GetByID(id) // Assuming you want to return updated todo
	ctx.JSON(http.StatusOK, updatedTodo)
}

func (controller *todoController) DeleteTodoByID(ctx *gin.Context) {
	id := ctx.Param("id")

	err := controller.repo.DeleteByID(id)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete todo"})
		return
	}

	ctx.JSON(http.StatusOK, gin.H{"message": "Todo deleted successfully"})
}
