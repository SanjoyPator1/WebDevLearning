package fileutils

import (
	"fmt"
	"os"
	"path/filepath"
)

func FileHandler() {
	rootPath, _ := os.Getwd()
	filePath := rootPath + "/" + "data"
	outputFile := filepath.Join("data", "output.txt")

	content, err := ReadTextFile(filePath + "/text.txt")
	if err != nil {
		fmt.Printf("Error reading file %v", err)
	} else {
		fmt.Println(content)
	}

	fmt.Println("Writing to file")
	newContent := fmt.Sprintf("Original: %v\n DOuble Original: %v%v", content, content, content)
	WriteToFile(outputFile, newContent)

}
