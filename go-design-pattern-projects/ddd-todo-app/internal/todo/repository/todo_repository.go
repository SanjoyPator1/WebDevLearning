package domain

import (
	"context"
	"fmt"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

// Todo represents a todo item
type Todo struct {
	ID          primitive.ObjectID `bson:"_id,omitempty" json:"id"`
	Title       string             `bson:"title" json:"title"`
	Description string             `bson:"description" json:"description"`
	// Add more fields as needed
}

// TodoRepository defines methods for interacting with todos in the database
type TodoRepository interface {
	GetAll() ([]*Todo, error)
	Get(id primitive.ObjectID) (*Todo, error)
	Create(todo *Todo) error
	Update(todo *Todo) error
	Delete(id primitive.ObjectID) error
}

// todoRepository represents the repository for todo operations
type todoRepository struct {
	collection *mongo.Collection
}

// NewTodoRepository creates a new instance of TodoRepository
func NewTodoRepository(collection *mongo.Collection) TodoRepository {
	return &todoRepository{
		collection: collection,
	}
}

// GetAll fetches all todos
func (r *todoRepository) GetAll() ([]*Todo, error) {
	ctx := context.TODO() // Use context appropriately in your application
	cur, err := r.collection.Find(ctx, bson.M{})
	if err != nil {
		return nil, err
	}
	defer cur.Close(ctx)

	var todos []*Todo
	for cur.Next(ctx) {
		var todo Todo
		if err := cur.Decode(&todo); err != nil {
			return nil, err
		}
		todos = append(todos, &todo)
	}
	if err := cur.Err(); err != nil {
		return nil, err
	}

	return todos, nil
}

// Get fetches a single todo by ID
func (r *todoRepository) Get(id primitive.ObjectID) (*Todo, error) {
	var todo Todo
	filter := bson.M{"_id": id}
	err := r.collection.FindOne(context.TODO(), filter).Decode(&todo)
	if err != nil {
		return nil, err
	}
	return &todo, nil
}

// Create creates a new todo
func (r *todoRepository) Create(todo *Todo) error {
	fmt.Println("Repository creating todo")
	result, err := r.collection.InsertOne(context.TODO(), todo)
	fmt.Printf("repository todo created: %v\n", result)
	if err != nil {
		return err
	}
	todo.ID = result.InsertedID.(primitive.ObjectID) // Ensure the inserted ID is set to the todo.ID
	fmt.Printf("repository todo id that will be attached is: %v\n", result.InsertedID.(primitive.ObjectID))
	fmt.Printf("repository todo updated: %v\n", todo)
	return nil
}

// Update updates an existing todo
func (r *todoRepository) Update(todo *Todo) error {
	filter := bson.M{"_id": todo.ID}
	update := bson.M{"$set": todo}
	_, err := r.collection.UpdateOne(context.TODO(), filter, update)
	if err != nil {
		return err
	}
	return nil
}

// Delete deletes a todo by ID
func (r *todoRepository) Delete(id primitive.ObjectID) error {
	filter := bson.M{"_id": id}
	_, err := r.collection.DeleteOne(context.TODO(), filter)
	if err != nil {
		return err
	}
	return nil
}
