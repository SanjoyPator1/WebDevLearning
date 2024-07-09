package models

import "go.mongodb.org/mongo-driver/bson/primitive"

// Todo represents a todo task
type Todo struct {
	ID          primitive.ObjectID `bson:"_id,omitempty"`
	Title       string             `bson:"title"`
	Description string             `bson:"description"`
	Completed   bool               `bson:"completed"`
}
