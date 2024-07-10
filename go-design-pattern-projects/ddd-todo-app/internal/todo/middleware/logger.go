package middleware

import (
	"log"
	"time"

	"github.com/gin-gonic/gin"
)

// Logger middleware logs each request
func Logger() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()

		// Process request
		c.Next()

		// Logging
		log.Printf("[%s] %s %s %v\n",
			c.Request.Method,
			c.Request.URL.Path,
			c.Request.RemoteAddr,
			time.Since(start),
		)
	}
}
