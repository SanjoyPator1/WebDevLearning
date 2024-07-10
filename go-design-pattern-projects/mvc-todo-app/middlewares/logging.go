package middlewares

import (
	"log"
	"time"

	"github.com/gin-gonic/gin"
)

func Logging() gin.HandlerFunc {
	return func(c *gin.Context) {
		t := time.Now()

		// before request
		c.Next()

		// after request
		latency := time.Since(t)
		status := c.Writer.Status()
		log.Printf("Request: %s %s | Status: %d | Latency: %v", c.Request.Method, c.Request.URL, status, latency)
	}
}
