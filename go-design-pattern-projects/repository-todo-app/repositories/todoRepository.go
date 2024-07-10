package repositories

import (
	"context"
	"errors"
	"log"
	"os"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"

	"repository-todo-app/config"
	"repository-todo-app/models"

	"github.com/go-redis/redis/v8"
)

type TodoRepository interface {
	GetAll() ([]models.Todo, error)
	GetByID(id string) (*models.Todo, error)
	Create(todo *models.Todo) error
	UpdateByID(id string, todo *models.Todo) error
	DeleteByID(id string) error
}

type todoRepository struct {
	collection *mongo.Collection
	redis      *redis.Client
}

func NewTodoRepository() (TodoRepository, error) {
	dbName := os.Getenv("MONGODB_DATABASE")
	if dbName == "" {
		return nil, errors.New("MONGODB_DATABASE environment variable is not set")
	}

	return &todoRepository{
		collection: config.MongoClient.Database(dbName).Collection("todos"),
		redis:      config.RedisClient,
	}, nil
}

func (repo *todoRepository) GetAll() ([]models.Todo, error) {
	var todos []models.Todo

	cursor, err := repo.collection.Find(context.Background(), bson.M{})
	if err != nil {
		log.Println("Error finding todos:", err)
		return nil, err
	}
	defer cursor.Close(context.Background())

	err = cursor.All(context.Background(), &todos)
	if err != nil {
		log.Println("Error decoding todos:", err)
		return nil, err
	}

	return todos, nil
}

func (repo *todoRepository) GetByID(id string) (*models.Todo, error) {
	var todo models.Todo

	oid, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		log.Println("Error converting id to ObjectID:", err)
		return nil, err
	}

	filter := bson.M{"_id": oid}
	err = repo.collection.FindOne(context.Background(), filter).Decode(&todo)
	if err != nil {
		log.Println("Error finding todo:", err)
		return nil, err
	}

	return &todo, nil
}

func (repo *todoRepository) Create(todo *models.Todo) error {
	todo.ID = primitive.NewObjectID() // Create a new ObjectID for the todo
	_, err := repo.collection.InsertOne(context.Background(), todo)
	if err != nil {
		log.Println("Error creating todo:", err)
		return err
	}

	err = repo.cacheTodoInRedis(todo)
	if err != nil {
		log.Println("Error caching todo in Redis:", err)
	}

	return nil
}

func (repo *todoRepository) UpdateByID(id string, todo *models.Todo) error {
	oid, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		log.Println("Error converting id to ObjectID:", err)
		return err
	}

	filter := bson.M{"_id": oid}
	update := bson.M{"$set": todo}

	result, err := repo.collection.UpdateOne(context.Background(), filter, update)
	if err != nil {
		log.Println("Error updating todo:", err)
		return err
	}

	if result.ModifiedCount == 0 {
		return errors.New("no todo found to update")
	}

	err = repo.cacheTodoInRedis(todo)
	if err != nil {
		log.Println("Error updating cached todo in Redis:", err)
	}

	return nil
}

func (repo *todoRepository) DeleteByID(id string) error {
	oid, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		log.Println("Error converting id to ObjectID:", err)
		return err
	}

	filter := bson.M{"_id": oid}

	result, err := repo.collection.DeleteOne(context.Background(), filter)
	if err != nil {
		log.Println("Error deleting todo:", err)
		return err
	}

	if result.DeletedCount == 0 {
		return errors.New("no todo found to delete")
	}

	err = repo.removeTodoFromRedis(id)
	if err != nil {
		log.Println("Error removing todo from Redis cache:", err)
	}

	return nil
}

func (repo *todoRepository) cacheTodoInRedis(todo *models.Todo) error {
	return repo.redis.Set(context.Background(), todo.ID.Hex(), todo, 0).Err()
}

func (repo *todoRepository) removeTodoFromRedis(id string) error {
	return repo.redis.Del(context.Background(), id).Err()
}
