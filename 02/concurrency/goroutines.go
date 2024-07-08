package concurrency

import (
    "fmt"
    "time"
)

// Function to print a message multiple times
func printMessage(msg string, times int) {
    for i := 0; i < times; i++ {
        fmt.Println(msg)
        time.Sleep(100 * time.Millisecond) // Sleep to simulate work and allow context switching
    }
}

// Function to demonstrate goroutines
func GoroutinesDemo() {
    // Start a new goroutine
    go printMessage("Goroutine 1", 5)

    // Start another goroutine
    go printMessage("Goroutine 2", 5)

    // Main goroutine work
    printMessage("Main Goroutine", 5)

    // Sleep to allow other goroutines to finish
    time.Sleep(1 * time.Second)
}