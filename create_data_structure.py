import json
import requests
import re
import os
import json
from bs4 import BeautifulSoup as bs


def main():
    with open('output/hrscurrent.json') as hrs_tree:
        hrs_data = json.load(hrs_tree)


        
    if not os.path.exists(path):
        os.makedirs(path)

    filename = img_alt + '.jpg'
    with open(os.path.join(path, filename), 'wb') as temp_file:
        temp_file.write(buff)
    outfile = open('output/section_text_example.json', 'w')
    json.dump(Chapter, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))
    print("Data scraped into section_text_example.json")


if __name__ == '__main__':
    main()
