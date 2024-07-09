package repositories

import (
	"context"
	"todo-app/models"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

// TodoRepository interacts with MongoDB for CRUD operations on todos
type TodoRepository struct {
	collection *mongo.Collection
}

// NewTodoRepository creates a new TodoRepository instance
func NewTodoRepository(db *mongo.Client) *TodoRepository {
	// Initialize TodoRepository with a MongoDB collection for tasks
	return &TodoRepository{
		collection: db.Database("todo-app").Collection("tasks"),
	}
}

// CreateTask inserts a new todo task into MongoDB
func (r *TodoRepository) CreateTask(ctx context.Context, task models.Todo) error {
	// InsertOne creates a new document in the collection
	_, err := r.collection.InsertOne(ctx, task)
	return err
}

// GetTasks retrieves all todo tasks from MongoDB
func (r *TodoRepository) GetTasks(ctx context.Context) ([]models.Todo, error) {
	// Find retrieves multiple documents from the collection
	cursor, err := r.collection.Find(ctx, bson.M{})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var tasks []models.Todo
	for cursor.Next(ctx) {
		var task models.Todo
		if err := cursor.Decode(&task); err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, nil
}

// GetTaskByID retrieves a specific todo task from MongoDB by its ID
func (r *TodoRepository) GetTaskByID(ctx context.Context, id string) (*models.Todo, error) {
	// Convert string ID to ObjectID
	objectID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		return nil, err
	}

	// FindOne retrieves a single document by its ID
	var task models.Todo
	err = r.collection.FindOne(ctx, bson.M{"_id": objectID}).Decode(&task)
	if err != nil {
		return nil, err
	}
	return &task, nil
}

// UpdateTask updates an existing todo task in MongoDB
func (r *TodoRepository) UpdateTask(ctx context.Context, id primitive.ObjectID, task models.Todo) error {
	// UpdateOne modifies a single document in the collection
	_, err := r.collection.UpdateOne(ctx, bson.M{"_id": id}, bson.M{"$set": task})
	return err
}

// DeleteTask deletes a todo task from MongoDB
func (r *TodoRepository) DeleteTask(ctx context.Context, id string) error {
	// Convert string ID to ObjectID
	objectID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		return err
	}

	// DeleteOne removes a single document from the collection
	_, err = r.collection.DeleteOne(ctx, bson.M{"_id": objectID})
	return err
}
