# Data comes from Johns Hopkins Univeristy. Thanks to them for making this public!
# https://github.com/CSSEGISandData/COVID-19
# You can find data beyond cumulative cases there!

'''
Test your code by analysing total confirmed cases over time
Each line in the file represents one day. The first value is confirmed cases on Jan 22nd.
The number of confirmed cases is "cumulative" meaning that it is the total number
of cases up until the current day. It will never go down!
'''

ITALY_PATH = 'italy.txt'

# This directory has files for all countries if you want to explore further
DATA_DIR = 'confirmed'


def main():
    file_open = open(ITALY_PATH)
    cases_list = []
    # pick numeric values only
    for case in file_open:
        case = case.strip()
        cases_list.append(case)
    print(cases_list)

    status_list = new_cases_change(cases_list)
    print(status_list)


def new_cases_change(covid_list):
    new_cases_per_day = []
    for i in range(len(covid_list)):
        if int(covid_list[i]) > int(covid_list[i - 1]):
            increase = int(covid_list[i]) - int(covid_list[i - 1])
            new_cases_per_day.append(str(increase))
        else:
            no_change = 0
            new_cases_per_day.append(no_change)
    return new_cases_per_day


if __name__ == '__main__':
    main()