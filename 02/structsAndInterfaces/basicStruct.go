package structs

import "fmt"

type User struct {
	id   int
	name string
}

func (u User) PrettyPrint() string {
	return "Pretty print: " + string(u.id) + " " + u.name
}

func TestBasicStruct() {
	var u1 User
	u1 = User{id: 1, name: "John Doe"}

	u2 := User{id: 2, name: "Marry Doe"}

	fmt.Println(u1.id, u1.name)
	fmt.Println(u2.id, u2.name)

	msg := u2.PrettyPrint()
	fmt.Println(msg)
}
