package service

import (
	"ddd-todo-app/internal/todo/domain"
	"fmt"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

// TodoService defines methods for todo operations
type TodoService interface {
	GetAll() ([]*domain.Todo, error)
	Get(id primitive.ObjectID) (*domain.Todo, error)
	Create(todo *domain.Todo) error
	Update(todo *domain.Todo) error
	Delete(id primitive.ObjectID) error
}

// todoService represents the service for todo operations
type todoService struct {
	repo domain.TodoRepository
}

// NewTodoService creates a new instance of TodoService
func NewTodoService(repo domain.TodoRepository) TodoService {
	return &todoService{
		repo: repo,
	}
}

// GetAll fetches all todos
func (s *todoService) GetAll() ([]*domain.Todo, error) {
	return s.repo.GetAll() // Correctly uses repo.GetAll() method
}

// Get fetches a single todo by ID
func (s *todoService) Get(id primitive.ObjectID) (*domain.Todo, error) {
	return s.repo.Get(id)
}

// Create creates a new todo
func (s *todoService) Create(todo *domain.Todo) error {
	fmt.Println("service creating todo")
	return s.repo.Create(todo)
}

// Update updates an existing todo
func (s *todoService) Update(todo *domain.Todo) error {
	return s.repo.Update(todo)
}

// Delete deletes a todo by ID
func (s *todoService) Delete(id primitive.ObjectID) error {
	return s.repo.Delete(id)
}
