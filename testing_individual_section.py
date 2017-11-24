import json
import requests
import re
from bs4 import BeautifulSoup as bs
from create_hrs_tree import section_text_data


def main():
    Section = {"chapter": '206E', "number": 2,
               "name": "Definitions", "repealed": False}

    section_text = section_text_data()

    print(section_text)
    Section['text'] = section_text

    outfile = open('output/testing_individual_section.json', 'w')
    json.dump(Section, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into testing_individual_section.json")


if __name__ == '__main__':
    main()
