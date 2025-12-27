"""
Exercise 1: See EXERCISES.md

"""

# simple
def fizz_buzz_1(count):
    for num in range(1,count+1):
        if num%3==0 and num%5==0:
            print("FizzBuzz")
        elif num%3 == 0:
            print("Fizz")
        elif num%5 == 0:
            print("Buzz")
        else:
            print(num)

# preferred
def fizz_buzz(count):
    for num in range(1, count+1):
        output = ""
        if num%3==0:
            output+="Fizz"
        if num%5==0:
            output+="Buzz"
        
        print(output or num)

if __name__ == "__main__":
    # Test your code
    fizz_buzz(20)
