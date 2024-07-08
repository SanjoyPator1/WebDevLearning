package typeAlias

import "fmt"

func MainType() {
	RunTypeAlias()

	// Define source and destination locations
	source := Location{Latitude: 40.7128, Longitude: -74.0060}       // New York City
	destination := Location{Latitude: 34.0522, Longitude: -118.2437} // Los Angeles

	// Calculate the distance between source and destination
	distance := source.DistanceBetween(destination)

	// Print the distance
	fmt.Printf("Distance between source and destination: %.2f km\n", distance)
}
