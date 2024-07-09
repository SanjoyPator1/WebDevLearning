package main

import (
	"fmt"
	"gowebserver/api"
	"net/http"
)

func handleHello(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("Hello from server"))
}

func main() {
	server := http.NewServeMux()
	server.HandleFunc(
		"/hello",
		handleHello)
	server.HandleFunc("/api/exhibitions", api.Get)
	server.HandleFunc("/api/exhibitions/new", api.Post)

	err := http.ListenAndServe(":3333", server)
	if err != nil {
		fmt.Println("Error while opening the server")
	}
}
