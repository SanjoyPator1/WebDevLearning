package testpackage

import "fmt"

func MyFunction(step int) {
	fmt.Println("step 1 & ", step)
	fmt.Println("step 2 & ", step)
	fmt.Println("step 3 ", step)
	myPrivateFunc()
}

func myPrivateFunc() {
	fmt.Println("step 4 - from my private function")
}
