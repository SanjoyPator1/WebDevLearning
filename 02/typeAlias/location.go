package typeAlias

import "math"

// Location represents geographical coordinates (latitude and longitude)
type Location struct {
    Latitude  float64
    Longitude float64
}

// DistanceBetween calculates the distance between two locations using the Haversine formula
func (src Location) DistanceBetween(dest Location) float64 {
    const earthRadiusKm = 6371.0

    lat1, lon1 := src.Latitude, src.Longitude
    lat2, lon2 := dest.Latitude, dest.Longitude

    // Convert degrees to radians
    dLat := degreesToRadians(lat2 - lat1)
    dLon := degreesToRadians(lon2 - lon1)

    // Apply the Haversine formula
    a := math.Sin(dLat/2)*math.Sin(dLat/2) +
        math.Cos(degreesToRadians(lat1))*math.Cos(degreesToRadians(lat2))*
            math.Sin(dLon/2)*math.Sin(dLon/2)
    c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))

    return earthRadiusKm * c
}

// Helper function to convert degrees to radians
func degreesToRadians(degrees float64) float64 {
    return degrees * (math.Pi / 180)
}