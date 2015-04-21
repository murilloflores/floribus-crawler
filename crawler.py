#!/usr/bin/env python 

import collections
import argparse
import requests
import json
import lxml.html
import unidecode

BASE_URL = 'http://www.consorciofenix.com.br'


def tokenize_and_analyze_string(string):
    tokens = string.split()
    final_tokens = [analyze_string(token) for token in tokens]
    return final_tokens

def analyze_string(string):
    analyzed_string = string.lower()
    if isinstance(analyzed_string, str):
        analyzed_string = unicode(analyzed_string, 'utf8')

    analyzed_string = unidecode.unidecode(analyzed_string)
    return analyzed_string

def fetch_lines_links():
    page = requests.get(BASE_URL+'/horarios')
    tree = lxml.html.fromstring(page.text)

    line_types_divs = tree.xpath('//div[@class="col-sm-4"]')

    for line_type_div in line_types_divs:
        line_type = line_type_div.findtext('h4')
        lines = line_type_div.find('ul').findall('li')
        
        for line in lines:
            line_link = line.find('a').get('href')
            yield { 'line_type': line_type, 'link': line_link }
        

def get_number_and_name(tree):

    name_and_number = tree.xpath('//*[@id="conteudo"]/div/div[1]/h1/a/text()')[0]
    
    pieces = name_and_number.split('-')
    number = pieces[-1].strip()
    name = '-'.join(pieces[:-1]).strip()

    return number, name


def get_timetables(tree):
    
    timetables = collections.defaultdict(dict)

    timetable_divs = tree.xpath('//*[@id="conteudo"]/div/div[1]/div')
    
    # The first one contains only additional info, so we remove it
    timetable_divs = timetable_divs[1:]

    for timetable_div in timetable_divs:
        timetable = timetable_div.xpath('.//a/text()[1]')
        timetable.sort()

        day_kind = timetable_div.xpath('.//div[2]')[0].get('data-semana')

        headline = timetable_div.xpath('.//div[1]/h4/text()')[0]
        headline_pieces = headline.split('-')
        
        starting_at = headline_pieces[1][6:].strip()
        timetables[starting_at][day_kind] = timetable
        
        if len(headline_pieces) > 2:
            additional_info = headline_pieces[2].strip()
            timetables[starting_at]['additional_info'] = additional_info
        else:
            timetables[starting_at]['additional_info'] = None

    return timetables

def get_line_information(line):

    page = None
    while page is None:
        try:
            page = requests.get(BASE_URL + line['link'])
        except:
            print 'net error'

    tree = lxml.html.fromstring(page.text)

    number, name = get_number_and_name(tree)
    timetables = get_timetables(tree)

    for idx, starting_at in enumerate(timetables):

        starting_at_additional_info = timetables[starting_at]['additional_info']
        del(timetables[starting_at]['additional_info'])

        search_tokens = _get_search_tokens(name, starting_at, starting_at_additional_info)

        line_info = {
            'id': str(number) + '.' + str(idx),
            'number': number,
            'name' : name,
            'starting_at': starting_at,
            'starting_at_additional_info': starting_at_additional_info,
            'searcheable_field' : search_tokens,
            'timetables': timetables[starting_at]
        }

        yield line_info


def _get_search_tokens(name, starting_at, starting_at_additional_info):
    search_tokens = tokenize_and_analyze_string(name)
    search_tokens.extend(tokenize_and_analyze_string(starting_at))

    if starting_at_additional_info:
        search_tokens.extend(tokenize_and_analyze_string(starting_at_additional_info))

    return list(set(search_tokens))


def get_lines_information(lines_links):
    for idx, line_link in enumerate(lines_links):
        print 'Getting line %d' % idx

        generated_lines = list(get_line_information(line_link))
        
        for generated_line in generated_lines:
            yield generated_line


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Crawl consorcionfenix website\'s and get information about bus lines operated by them')
    parser.add_argument('output', type=argparse.FileType('w'))
    args = parser.parse_args()

    print 'Will fetch lines list.'
    lines_links_list = list(fetch_lines_links())

    print '%d lines on the list' % len(lines_links_list)

    print 'Will get lines information.'
    lines = list(get_lines_information(lines_links_list))

    print 'Will write the output file.'
    for line in lines:
        args.output.write(json.dumps(line) + '\n')
