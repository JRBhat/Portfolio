"""
File: khansole_academy.py
-------------------------
This program randomly generates simple addition problems for the user, reads in the answer from the user, and then
checks to see if they got it right or wrong, until the user appears to have mastered the
material.
"""
import random
#A constant for the number of times the user has to answer correctly in a row before winning
CORRECT_ANSWERS_ROW = 3


def main():
    """
    program adds two randomly generated constants and stores the solution
    It then asks the user for the solution, and checks the user input with the stored solution
    If solution is correct, update counter, else reset it.
    """
    count_tries = 0
    while True:
        num1 = random.randint(10, 99)
        num2 = random.randint(10, 99)
        num_sum = num1 + num2
        print(f"What is {num1} + {num2}?")
        answer = int(input("Your answer: "))
        if answer != num_sum:
            count_tries = 0
            print(f"Incorrect. The expected answer is {num_sum}.")

        elif answer == num_sum:
            count_tries += 1
            print(f"Correct! You've gotten {count_tries} correct in a row.")

            if count_tries == CORRECT_ANSWERS_ROW :
                print("Congratulations! You have mastered addition.")
                return False




# This provided line is required at the end of a Python file
# to call the main() function.
if __name__ == '__main__':
    main()
