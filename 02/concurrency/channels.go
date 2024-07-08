package concurrency

import (
    "fmt"
    "time"
)

// Function to send a message to a channel
func sendMessage(ch chan string, msg string) {
    time.Sleep(1 * time.Second) // Simulate work
    ch <- msg // Send the message to the channel
}

// Function to demonstrate channels
func ChannelsDemo() {
    // Create a channel of type string
    ch := make(chan string)

    // Start a goroutine to send a message
    go sendMessage(ch, "Hello from Goroutine")

    // Receive the message from the channel
    msg := <-ch
    fmt.Println(msg) // Output: Hello from Goroutine
}