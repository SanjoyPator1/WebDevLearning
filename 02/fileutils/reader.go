package fileutils

import "os"

func ReadTextFile(filename string) (string, error) {
	content, err := os.ReadFile((filename))
	if err != nil {
		return "", err
	} else {
		return string(content), nil
	}
}
