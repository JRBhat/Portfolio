import time
import random

from termcolor import colored

PHASE_TIME_S = 10
'''
https://docs.google.com/document/d/1HTaFLW0rLy_0mJ52L6Sjb1Nl-K_szFclal2rUjuoKr8/preview'''

def main():
    print_intro()
    is_phase_1 = True
    count_1 = run_phase(is_phase_1)
    is_phase_2 = False
    count_2 = run_phase(is_phase_2)
    print(f"Total correct in Phase 1 : {count_1}")
    print(f"Total correct in Phase 2 : {count_2}")


def print_intro():
    '''
    Function: print intro
    Prints a simple welcome message
    '''
    print('This is the Stroop test! Name the font-color used:')
    print_in_color('red', 'red')
    print_in_color('blue', 'blue')
    print_in_color('pink', 'pink')
    print("............ ")


def random_color_name():
    '''
    Function: random color
    Returns a string (either red, blue or pink) with equal likelihood
    '''
    return random.choice(['red', 'blue', 'pink'])


def print_in_color(text, font_color):
    '''
    Function: print in color
    Just like "print" but this time, you can specify the font-color
    '''
    if font_color == 'pink':  # magenta is a lot to type...
        font_color = 'magenta'
    print(colored(text, font_color, attrs=['bold']))


def run_single_test(abool):
    if abool == False:
        correct1 = 0
        color_name1 = random_color_name()
        color_of_font1 = random_color_name()
        print_in_color(color_name1, color_of_font1)
        ans1 = input("What color ink is the word written in? ")
        if ans1 == color_of_font1:
            return True
        else:
            print(f"Wrong! The correct color is {color_of_font1}")
            return False
    else:
        correct2 = 0
        color_name2 = random_color_name()
        color_of_font2 = color_name2
        print_in_color(color_name2, color_of_font2)
        ans2 = input("What color ink is the word written in? ")
        if ans2 == color_of_font2:
            return True
        else:
            print(f"Wrong! The correct color is {color_of_font2}")
            return False


def run_phase(abool):
    start = time.time()
    correct = 0
    tries = 0
    while time.time() - start < PHASE_TIME_S:
        result = run_single_test(abool)
        tries += 1
        if result == True:
            print(result)
            correct += 1
    return str(correct) + ' times correct out of ' + str(tries) + ' tries'


if __name__ == '__main__':
    main()