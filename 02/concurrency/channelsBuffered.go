package concurrency

import (
    "fmt"
    "time"
)

// Function to send multiple messages to a channel
func sendMessages(ch chan string) {
    ch <- "Hello"
    ch <- "World"
    time.Sleep(1 * time.Second) // Simulate work
    ch <- "from"
    ch <- "Buffered Channel"
    close(ch) // Close the channel to indicate no more values will be sent
}

// Function to demonstrate buffered channels
func ChannelsBufferedDemo() {
    // Create a buffered channel with a capacity of 2
    ch := make(chan string, 2)

    // Start a goroutine to send messages
    go sendMessages(ch)

    // Receive messages from the channel
    for msg := range ch {
        fmt.Println(msg)
    }
}