import json
import requests
import re
import os
import json
from bs4 import BeautifulSoup as bs


def main():
    with open('output/hrscurrent.json') as hrs_tree:
        hrs_data = json.load(hrs_tree)

    for division in hrs_data:
        titles = division['titles']

        for title in titles:
            chapters = title['chapters']

            for chapter in chapters:
                if chapter['repealed']:
                    create_path(division, title, chapter, None)
                else:
                    sections = chapter['sections']
                    for section in sections:
                        create_path(division, title, chapter, section)

    print('Data structure created using hrscurrent.json')


def create_path(division, title, chapter, section):
    division_json = {'name': division['name'],
                     'number': division['number']}

    title_json = {'name': title['name'],
                  'number': title['number']}

    chapter_json = {'name': chapter['name'],
                    'number': chapter['number'],
                    'repealed': chapter['repealed']}

    path = 'output/hrscurrent/division/{}/title/{}/chapter/{}/section/'.format(
        division['number'], title['number'], chapter['number'])

    if not os.path.exists(path):
        os.makedirs(path)

    outfile = open('output/hrscurrent/division/' +
                   str(division['number']) + '.json', 'w')
    json.dump(division_json, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))

    outfile = open('output/hrscurrent/division/' + str(division['number']) +
                   '/title/' + str(title['number']) + '.json', 'w')
    json.dump(title_json, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))

    outfile = open('output/hrscurrent/division/' + str(division['number']) +
                   '/title/' + str(title['number']) +
                   '/chapter/' + str(chapter['number']) + '.json', 'w')
    json.dump(chapter_json, outfile, sort_keys=True,
              indent=4, separators=(',', ': '))

    if section is not None:
        try:
            section_json = {'name': section['name'],
                            'number': section['number'],
                            'text': section['text']}

            outfile = open('output/hrscurrent/division/' + str(division['number']) +
                           '/title/' + str(title['number']) +
                           '/chapter/' + str(chapter['number']) +
                           '/section/' + str(chapter['number']) + '-' + str(section['number']) + '.json', 'w')
            json.dump(section_json, outfile, sort_keys=True,
                      indent=4, separators=(',', ': '))
        except:
            print(str(chapter['number']) + '-' +
                  str(section['number']) + ' doesnt contain a text field')


if __name__ == '__main__':
    main()
