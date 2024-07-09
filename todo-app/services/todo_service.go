package services

import (
	"context"
	"encoding/json"
	"todo-app/models"
	"todo-app/repositories"

	"github.com/go-redis/redis/v8"
	"go.mongodb.org/mongo-driver/bson/primitive" // Import primitive package for ObjectID
)

// TodoService handles business logic for todo tasks
type TodoService struct {
	repository  *repositories.TodoRepository // repository is used to interact with MongoDB
	redisClient *redis.Client                // redisClient is used for caching
}

// CreateTaskInput defines the input structure for creating a task
type CreateTaskInput struct {
	Title       string `json:"title"`
	Description string `json:"description"`
}

// UpdateTaskInput defines the input structure for updating a task
type UpdateTaskInput struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Completed   bool   `json:"completed"`
}

// NewTodoService creates a new TodoService instance
func NewTodoService(repository *repositories.TodoRepository, redisClient *redis.Client) *TodoService {
	return &TodoService{repository: repository, redisClient: redisClient}
}

// CreateTask creates a new todo task
func (s *TodoService) CreateTask(ctx context.Context, input CreateTaskInput) error {
	// Create a new todo task based on input
	task := models.Todo{
		Title:       input.Title,
		Description: input.Description,
		Completed:   false,
	}
	// Call repository method to insert task into MongoDB
	if err := s.repository.CreateTask(ctx, task); err != nil {
		return err
	}
	// Clear the cache after creating the task
	return s.clearCache(ctx)
}

// GetTasks retrieves all todo tasks, using cache if available
func (s *TodoService) GetTasks(ctx context.Context) ([]models.Todo, error) {
	// Try to fetch tasks from cache
	cachedTasks, err := s.redisClient.Get(ctx, "tasks").Result()
	if err == nil {
		// If cached tasks exist, unmarshal them from JSON
		var tasks []models.Todo
		if err := json.Unmarshal([]byte(cachedTasks), &tasks); err == nil {
			return tasks, nil
		}
	}

	// If no cached tasks or unmarshaling error, fetch from MongoDB
	tasks, err := s.repository.GetTasks(ctx)
	if err != nil {
		return nil, err
	}

	// Marshal tasks into JSON and store in cache
	taskData, err := json.Marshal(tasks)
	if err == nil {
		s.redisClient.Set(ctx, "tasks", taskData, 0)
	}

	return tasks, nil
}

// GetTaskByID retrieves a specific todo task by its ID
func (s *TodoService) GetTaskByID(ctx context.Context, id string) (*models.Todo, error) {
	return s.repository.GetTaskByID(ctx, id)
}

// UpdateTask updates an existing todo task
func (s *TodoService) UpdateTask(ctx context.Context, id string, input UpdateTaskInput) error {
	// Convert string ID to ObjectID
	objectID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		return err
	}
	// Create updated task based on input
	task := models.Todo{
		Title:       input.Title,
		Description: input.Description,
		Completed:   input.Completed,
	}
	// Call repository method to update task in MongoDB
	if err := s.repository.UpdateTask(ctx, objectID, task); err != nil {
		return err
	}
	// Clear the cache after updating the task
	return s.clearCache(ctx)
}

// DeleteTask deletes a todo task
func (s *TodoService) DeleteTask(ctx context.Context, id string) error {
	// Call repository method to delete task from MongoDB
	if err := s.repository.DeleteTask(ctx, id); err != nil {
		return err
	}
	// Clear the cache after deleting the task
	return s.clearCache(ctx)
}

// clearCache clears the tasks cache
func (s *TodoService) clearCache(ctx context.Context) error {
	return s.redisClient.Del(ctx, "tasks").Err()
}
