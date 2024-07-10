package controllers

import (
	"mvc-todo-app/config"
	"mvc-todo-app/models"
	"net/http"

	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

func GetTodos(c *gin.Context) {
	var todos []models.Todo
	collection := config.MongoClient.Database("tododb").Collection("todos")
	cursor, err := collection.Find(config.Ctx, bson.M{})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	defer cursor.Close(config.Ctx)

	if err = cursor.All(config.Ctx, &todos); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, todos)
}

func CreateTodo(c *gin.Context) {
	var todo models.Todo
	if err := c.ShouldBindJSON(&todo); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	collection := config.MongoClient.Database("tododb").Collection("todos")
	result, err := collection.InsertOne(config.Ctx, todo)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	todo.ID = result.InsertedID.(primitive.ObjectID)
	c.JSON(http.StatusCreated, todo)
}

func GetTodoByID(c *gin.Context) {
	id, _ := primitive.ObjectIDFromHex(c.Param("id"))
	var todo models.Todo
	collection := config.MongoClient.Database("tododb").Collection("todos")
	err := collection.FindOne(config.Ctx, bson.M{"_id": id}).Decode(&todo)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Todo not found"})
		return
	}
	c.JSON(http.StatusOK, todo)
}

func UpdateTodoByID(c *gin.Context) {
	id, err := primitive.ObjectIDFromHex(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
		return
	}

	var todo models.Todo
	if err := c.ShouldBindJSON(&todo); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	collection := config.MongoClient.Database("tododb").Collection("todos")
	filter := bson.M{"_id": id}
	update := bson.M{"$set": bson.M{"title": todo.Title, "description": todo.Description}}

	result, err := collection.UpdateOne(config.Ctx, filter, update)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if result.MatchedCount == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "Todo not found"})
		return
	}

	todo.ID = id
	c.JSON(http.StatusOK, todo)
}

func DeleteTodoByID(c *gin.Context) {
	id, _ := primitive.ObjectIDFromHex(c.Param("id"))
	collection := config.MongoClient.Database("tododb").Collection("todos")
	_, err := collection.DeleteOne(config.Ctx, bson.M{"_id": id})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusNoContent, nil)
}
