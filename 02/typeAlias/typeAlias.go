package typeAlias

import "fmt"

// Define a new type 'distance' as a float64 representing miles
type distance float64

// Define a new type 'distanceKm' as a float64 representing kilometers
type distanceKm float64

// Method to convert miles to kilometers
func (miles distance) ToKm() distanceKm {
	return distanceKm(miles * 1.60934) // Conversion factor from miles to kilometers
}

// Method to convert kilometers to miles
func (km distanceKm) ToMiles() distance {
	return distance(km / 1.60934) // Conversion factor from kilometers to miles
}

// Function to demonstrate the usage of the defined types and methods
func RunTypeAlias() {
	// Create an instance of 'distance' type representing 4.5 miles
	d := distance(4.5)
	// Convert miles to kilometers using the ToKm method
	km := d.ToKm()
	// Convert kilometers back to miles using the ToMiles method
	miles := km.ToMiles()

	// Print the results
	fmt.Println("distance in miles:", d)
	fmt.Println("distance in kilometers:", km)
	fmt.Println("converted back to miles:", miles)
}
