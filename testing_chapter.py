import json
import requests
import re
from bs4 import BeautifulSoup as bs
from create_hrs_tree import get_section_text_data


def main():
    Chapter = {"number": 412,
               "name": "UNIFORM CHILD-CUSTODY JURISDICTION AND ENFORCEMENT ACT",
               "repealed": False}

    url = 'http://www.capitol.hawaii.gov/hrscurrent/Vol08_Ch0401-0429/HRS0412/HRS_0412-.htm'
    Sections = get_section_text_data(url)

    if Sections is None:
        Chapter['repealed'] = True
    else:
        Chapter["sections"] = Sections

    outfile = open('output/testing_chapter.json', 'w')
    json.dump(Chapter, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into testing_chapter.json")


if __name__ == '__main__':
    main()
