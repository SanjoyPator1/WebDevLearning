package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// AuthMiddleware is a simple middleware for authentication
func AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Implement your authentication logic here
		token := c.GetHeader("Authorization")
		if token == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
			c.Abort()
			return
		}
		c.Next()
	}
}
