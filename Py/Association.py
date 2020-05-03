import random
import time

PHASE_TIME_S = 10


def main():
    is_phase_1 = True
    print_intro(is_phase_1)
    count_1 = run_phase(is_phase_1)
    is_phase_1 = False
    print_intro(is_phase_1)
    count_2 = run_phase(is_phase_1)
    print(f"Total correct in Phase 1 : {count_1}")
    print(f"Total correct in Phase 2 : {count_2}")


def print_intro(is_phase_1):
    # greets the user and displays the different choices at his disposal
    if is_phase_1:
        print('Association test, standard')
    else:
        print('Association test, flipped')
    print('You will be asked to answer three questions.')
    print('You should associate animals as follows:')
    print('puppy', get_association('puppy', is_phase_1))
    print('panda', get_association('panda', is_phase_1))
    print('spider', get_association('spider', is_phase_1))
    print('bat', get_association('bat', is_phase_1))
    input('Press enter to start... ')


def random_animal():
    # randomly chooses an animal from a set returns selected
    return random.choice(['puppy', 'panda', 'spider', 'bat'])


def get_association(animal, is_phase_1):
    # associates stereotypical or non-stereotypical inferences depending on the phase and animal name
    if is_phase_1:
        if animal == 'puppy' or animal == 'panda':
            return 'cute'
        elif animal == 'bat' or animal == 'spider':
            return 'scary'
    else:
        if animal == 'puppy' or animal == 'panda':
            return 'scary'
        elif animal == 'bat' or animal == 'spider':
            return 'cute'


def run_single_test(is_phase_1):
    # runs a single  test asking the user's association type for a particular animal provided
    if is_phase_1:
        rand_animal = random_animal()
        print(rand_animal)
        answer = get_association(rand_animal, is_phase_1)
        user_input = input("Type of association: ")
        if user_input == answer:
            return True
        else:
            print(f"Wrong! The correct answer was {answer}")
            return False
    else:
        rand_animal = random_animal()
        print(rand_animal)
        answer = get_association(rand_animal, is_phase_1)
        user_input = input("Type of association: ")
        if user_input == answer:
            return True
        else:
            print(f"Wrong! The correct answer was {answer}")
            return False


def run_phase(is_phase_1):
    start = time.time()
    correct = 0
    tries = 0
    while time.time() - start < PHASE_TIME_S:
        result = run_single_test(is_phase_1)
        tries += 1
        if result == True:
            print(result)
            correct += 1
    return str(correct) + ' times correct out of ' + str(tries) + ' tries'


if __name__ == '__main__':
    main()