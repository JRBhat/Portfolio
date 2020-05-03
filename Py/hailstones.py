"""
File: hailstones.py
-------------------
This is a file for the optional Hailstones problem, if
you'd like to try solving it.
"""

def main():
    """
The program pciks a positive integer from the user. If the number is even, then
it is divided by two, but if it is odd it is multiplied by 3 and added to 2.
The resulting answer then repeats through the same process as before generating
the 'Hailstone sequence'. The sequence generation stops at 1 and the number of steps
taken is printed.
    """
    count = 0
    user_num = int(input("Please enter a number: "))

    while user_num != 1:

        if user_num % 2 == 0:
            num_even_in = user_num
            user_num = user_num / 2
            count += 1
            print(f"{int(num_even_in)} is even, so I take half: {int(user_num)}")

        elif user_num % 2 != 0:
            num_odd_in = user_num
            user_num = (user_num * 3) + 1
            count += 1
            print(f"{int(num_odd_in)} is odd, so I make 3n+1:{int(user_num)}")

    print(f"The process took {count} steps to reach 1.")



# This provided line is required at the end of a Python file
# to call the main() function.
if __name__ == '__main__':
    main()
