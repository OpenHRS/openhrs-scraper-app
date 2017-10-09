import json
import requests
import re
from bs4 import BeautifulSoup as bs


def sectionTextData():
    """ Preps the data by getting rid of bolded text """
    baseURL = 'http://www.capitol.hawaii.gov/hrscurrent/Vol02_Ch0046-0115/HRS0103D/HRS_0103D-0104.htm'
    htmlToParse = requests.get(baseURL)
    soup = bs(htmlToParse.text, 'lxml')

    return soup.find('div', {'class': 'WordSection1'}).get_text().replace('\r\n', ' ')


def main():
    Section = {"chapter": '206E', "number": 2,
               "name": "Definitions", "repealed": False}

    section_text = sectionTextData()

    print(section_text)
    Section['text'] = section_text

    outfile = open('output/section_example.json', 'w')
    json.dump(Section, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into section_example.json")


if __name__ == '__main__':
    main()
