package structs

import "fmt"

// Define the Speaker interface
type Speaker interface {
	Speak() string
}

// Define the Person struct
type Person struct {
	Name string
}

// Implement the Speak method for Person
func (p Person) Speak() string {
	return fmt.Sprintf("%s says: Hello!", p.Name)
}

// Define the Dog struct
type Dog struct {
	Breed string
}

// Implement the Speak method for Dog
func (d Dog) Speak() string {
	return fmt.Sprintf("The %s barks!", d.Breed)
}

// Function that accepts a Speaker and calls its Speak method
func MakeSpeak(s Speaker) {
	fmt.Println(s.Speak())
}

func MainInterfaces() {
	// Create instances of Person and Dog
	john := Person{Name: "John"}
	bulldog := Dog{Breed: "Bulldog"}

	// Use the MakeSpeak function with different Speaker implementations
	MakeSpeak(john)    // Output: John says: Hello!
	MakeSpeak(bulldog) // Output: The Bulldog barks!
}
