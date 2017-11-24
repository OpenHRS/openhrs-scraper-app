import json
import requests
import re
from bs4 import BeautifulSoup as bs
from create_hrs_tree import get_section_text_data


def main():
    Section = {"name": 'Risk of loss',
               "number": '2A-219'}
    baseURL = 'http://www.capitol.hawaii.gov/hrscurrent/Vol11_Ch0476-0490/HRS0490/HRS_0490-.htm'

    section_text = get_section_text_data(baseURL, "2A-219")

    Section['text'] = section_text

    outfile = open('output/testing_individual_section.json', 'w')
    json.dump(Section, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into testing_individual_section.json")


if __name__ == '__main__':
    main()
