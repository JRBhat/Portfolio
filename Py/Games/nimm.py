"""
File: nimm.py
-------------------------
Add your comments here.
"""
import random
#create constant 'stones_left' and set it to 20


def main():
    """

    """
    STONES_LEFT = 20
    print(f"There are {STONES_LEFT} stones left")
    player = 1
# write program to remove stones and print out how many are left
    while True:
        if player == 1:
            stones_taken = int(input("Player 1 would you like to remove 1 or 2 stones? "))
            #remove stones according to user input
            while stones_taken != 1 and stones_taken != 2:
                stones_taken_check_1 = int(input("Please enter 1 or 2: "))

                if stones_taken_check_1 == 1:
                    STONES_LEFT -= 1
                    player += 1
                    if STONES_LEFT == 0:
                        print(f"\nPlayer {player} wins!")
                        return False
                    print(f"\nThere are {STONES_LEFT} stones left")
                    break

                elif stones_taken_check_1 == 2:
                    STONES_LEFT -= 2
                    player += 1
                    if STONES_LEFT == 0:
                        print(f"\nPlayer {player} wins!")
                        return False
                    print(f"\nThere are {STONES_LEFT} stones left")
                    break

            if stones_taken == 1:
                STONES_LEFT -= 1
                player += 1
                if STONES_LEFT == 0:
                    print(f"\nPlayer {player} wins!")
                    return False
                print(f"\nThere are {STONES_LEFT} stones left")


            elif stones_taken == 2:
                STONES_LEFT -= 2
                player += 1
                if STONES_LEFT == 0:
                    print(f"\nPlayer {player} wins!")
                    return False
                print(f"\nThere are {STONES_LEFT} stones left")


        elif player == 2:
                stones_taken = int(input("Player 2 would you like to remove 1 or 2 stones? "))
                # remove stones according to user input
                while stones_taken != 1 and stones_taken != 2:
                    stones_taken_check_2 = int(input("Please enter 1 or 2: "))

                    if stones_taken_check_2 == 1:
                        STONES_LEFT -= 1
                        player -= 1
                        if STONES_LEFT == 0:
                            print(f"\nPlayer {player} wins!")
                            return False
                        print(f"\nThere are {STONES_LEFT} stones left")
                        break


                    elif stones_taken_check_2 == 2:
                        STONES_LEFT -= 2
                        player -= 1
                        if STONES_LEFT == 0:
                            print(f"\nPlayer {player} wins!")
                            return False
                        print(f"\nThere are {STONES_LEFT} stones left")
                        break

                if stones_taken == 1:
                    STONES_LEFT -= 1
                    player -= 1
                    if STONES_LEFT == 0:
                        print(f"\nPlayer {player} wins!")
                        return False
                    print(f"\nThere are {STONES_LEFT} stones left")


                elif stones_taken == 2:
                    STONES_LEFT -= 2
                    player -= 1
                    if STONES_LEFT == 0:
                        print(f"\nPlayer {player} wins!")
                        return False
                    print(f"\nThere are {STONES_LEFT} stones left")



# This provided line is required at the end of a Python file
# to call the main() function.
if __name__ == '__main__':
    main()
