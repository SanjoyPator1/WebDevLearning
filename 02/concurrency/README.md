# Concurrency Package

This package contains examples and demonstrations of various concurrency features in Go, including goroutines, unbuffered channels, and buffered channels.

## File Descriptions

### `goroutines.go`

**Purpose**: Demonstrates the use of goroutines in Go.

- **Goroutines**: Lightweight threads managed by the Go runtime. Multiple goroutines can run concurrently, making it possible to perform various tasks simultaneously without significant overhead.
- **Example**: A function that prints messages is run in multiple goroutines. The main function also runs a similar task concurrently. The goroutines and the main function perform their tasks in parallel, showcasing concurrency in Go.

### `channels.go`

**Purpose**: Demonstrates the use of unbuffered channels in Go.

- **Channels**: Provide a way for goroutines to communicate and synchronize their execution. Channels can be thought of as pipes through which data flows.
- **Unbuffered Channels**: Channels where the sender waits for the receiver to receive the value. They ensure synchronization between sending and receiving goroutines.
- **Example**: A goroutine sends a message to a channel, and the main function receives and prints the message. This demonstrates basic channel communication and synchronization.

### `channelsBuffered.go`

**Purpose**: Demonstrates the use of buffered channels in Go.

- **Buffered Channels**: Channels with a capacity to hold a fixed number of values. Senders can send values to the channel without an immediate receiver, up to the buffer's capacity.
- **Example**: A goroutine sends multiple messages to a buffered channel. The main function receives and prints these messages, showcasing how buffered channels can handle multiple values without immediate synchronization.

### `execute.go`

**Purpose**: Contains a function to execute all concurrency demos in the package.

- **Functionality**: Calls all the demo functions (`GoroutinesDemo`, `ChannelsDemo`, `ChannelsBufferedDemo`) to run the concurrency examples in sequence.
- **Usage**: This function can be called from the main function to demonstrate all the concurrency features implemented in the package.

## Usage

To run the concurrency demos, call the `ExecuteAll` function from your `main.go` file:

```go
package main

import (
    "your-project/concurrency"
)

func main() {
    concurrency.ExecuteAll()
}
```
