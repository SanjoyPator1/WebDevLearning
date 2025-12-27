"""
Exercise 2: See EXERCISES.md

TODO: Implement solution here
"""

# Your code here
def is_palindrome_1(sentence):
    sentence = sentence.lower()
    print(f"\nsentence is {sentence}")

    l,r =0, len(sentence) - 1

    while l<r:
        while l<r and not sentence[l].isalnum():
            print(f"Left char = {sentence[l]} not alnum moving left by one ptr right ")
            l+=1

        while l<r and not sentence[r].isalnum():
            print(f"Right char = {sentence[r]} not alnum moving right by one ptr left ")
            r-=1

        print(f"left_char = {sentence[l]} and right_char = {sentence[r]}")

        # if the left side and right side dont match
        if sentence[l] != sentence[r]:
            return False
        
        l+=1
        r-=1

    return True

def is_palindrome(sentence):
    cleaned = "".join(
        ch.lower() for ch in sentence if ch.isalnum()
    )

    return cleaned == cleaned[::-1]


if __name__ == "__main__":
    test_cases = [
        "racecar",
        "hello",
        "A man a plan a canal Panama",
        "Was it a car or a cat I saw?",
        "Python"
    ]

    for text in test_cases:
        result = "Palindrome" if is_palindrome(text) else "Not a palindrome"
        print(f'"{text}" → {result}')

