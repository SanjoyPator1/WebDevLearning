package structs

import "fmt"

// Custom type Duration as a float32
type Duration float32


// Struct Course representing a course with various fields
type Course struct {
    Id         int
    Name       string
    Slug       string
    Legacy     bool
    Duration   Duration
    Instructor Instructor
}

// Method to get the course name
func (c Course) GetName() string {
    return c.Name
}

// Struct Workshop that embeds Course and adds additional fields
type Workshop struct {
    Course
    Venue     string
    Attendees int
}

// Method to get the workshop name
func (w Workshop) GetName() string {
    return w.Name
}

// Define the Signable interface
type Signable interface {
    GetName() string
}

// Factory function for creating a new Course instance
func NewCourse(id int, name string, duration Duration, instructor Instructor) Course {
    return Course{
        Id:         id,
        Name:       name,
        Duration:   duration,
        Instructor: instructor,
    }
}

// Factory function for creating a new Workshop instance
func NewWorkshop(course Course, venue string, attendees int) Workshop {
    return Workshop{
        Course:    course,
        Venue:     venue,
        Attendees: attendees,
    }
}

// Test function to demonstrate the use of interfaces
func TestStructAndInterfaces() {
    // Create instances of Course and Workshop
    jonathan := NewInstructor("Jonathan", "Long")
    goCourse := NewCourse(4, "Go course", 12.5, jonathan)
    goWorkshop := NewWorkshop(goCourse, "Online", 150)

    // Create an array of Signable and add Course and Workshop instances
    var signables []Signable
    signables = append(signables, goCourse)
    signables = append(signables, goWorkshop)

    // Iterate over the array and print the names
    for _, s := range signables {
        fmt.Printf("Signable: %v\n", s.GetName())
    }
}
