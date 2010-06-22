#! /usr/bin/env python
"""
Find the distance between different places in India.

Usage: distance.py <source> <destination>

@author: Sreejith K <sreejithemk@gmail.com>
"""

import os
import sys
import urllib2
from HTMLParser import HTMLParser
from urlparse import urljoin
import difflib

SITE_URL = 'http://distancebetween.in'

class FuzzyDict(dict):
    "Provides a dictionary that performs fuzzy lookup"
    def __init__(self, items = None, cutoff = .6):
        """Construct a new FuzzyDict instance

        items is an dictionary to copy items from (optional)
        cutoff is the match ratio below which mathes should not be considered
        cutoff needs to be a float between 0 and 1 (where zero is no match
        and 1 is a perfect match)"""
        super(FuzzyDict, self).__init__()

        if items:
            self.update(items)
        self.cutoff =  cutoff

        # short wrapper around some super (dict) methods
        self._dict_contains = lambda key: \
            super(FuzzyDict,self).__contains__(key)

        self._dict_getitem = lambda key: \
            super(FuzzyDict,self).__getitem__(key)

    def _search(self, lookfor, stop_on_first = False):
        """Returns the value whose key best matches lookfor

        if stop_on_first is True then the method returns as soon
        as it finds the first item
        """

        # if the item is in the dictionary then just return it
        if self._dict_contains(lookfor):
            return True, lookfor, self._dict_getitem(lookfor), 1

        # set up the fuzzy matching tool
        ratio_calc = difflib.SequenceMatcher()
        ratio_calc.set_seq1(lookfor)

        # test each key in the dictionary
        best_ratio = 0
        best_match = None
        best_key = None
        for key in self:

            # if the current key is not a string
            # then we just skip it
            try:
                # set up the SequenceMatcher with other text
                ratio_calc.set_seq2(key)
            except TypeError:
                continue

            # we get an error here if the item to look for is not a
            # string - if it cannot be fuzzy matched and we are here
            # this it is defintely not in the dictionary
            try:
            # calculate the match value
                ratio = ratio_calc.ratio()
            except TypeError:
                break

            # if this is the best ratio so far - save it and the value
            if ratio > best_ratio:
                best_ratio = ratio
                best_key = key
                best_match = self._dict_getitem(key)

            if stop_on_first and ratio >= self.cutoff:
                break

        return (
            best_ratio >= self.cutoff,
            best_key,
            best_match,
            best_ratio)


    def __contains__(self, item):
        "Overides Dictionary __contains__ to use fuzzy matching"
        if self._search(item, True)[0]:
            return True
        else:
            return False

    def __getitem__(self, lookfor):
        "Overides Dictionary __getitem__ to use fuzzy matching"
        matched, key, item, ratio = self._search(lookfor)

        if not matched:
            raise KeyError(
                "'%s'. closest match: '%s' with ratio %.3f"%
                    (str(lookfor), str(key), ratio))

        return item

class LocationFinder(HTMLParser):
    """
    Finds the supported sources and destinations.
    """
    _is_source_list = False
    _is_destination_list = False
    _sources = {}
    _destinations = {}

    _current_id = None
    _current_location = None

    def handle_starttag(self, tag, attrs):
        if tag == 'select':
            if attrs == [('name', 'selectcity1'), ('id', 'selectcity1')]:
                self._is_source_list = True
            elif attrs == [('name', 'selectcity2'), ('id', 'selectcity2')]:
                self._is_destination_list = True
        elif tag == 'option':
            if self._is_source_list or self._is_destination_list:
                self._current_id = attrs[0][1]

    def handle_endtag(self, tag):
        if tag == 'select':
            if self._is_source_list:
                self._is_source_list = False
            elif self._is_destination_list:
                self._is_destination_list = False

    def handle_data(self, data):
        if data.isspace(): return
        if self._is_source_list:
            self._sources[data] = self._current_id
        if self._is_destination_list:
            self._destinations[data] = self._current_id

class DistanceFinder(HTMLParser):
    _is_distance = False
    _record = False
    _distance = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'span':
            if attrs == [('style', 'color:#FF4500;')] and self._is_distance:
                self._record = True
            if attrs == [('class', 'show_distance')]:
                self._is_distance = True

    def handle_endtag(self, tag):
        if tag == 'span':
            if self._is_distance:
                self._is_distance = False
                self._record = False

    def handle_data(self, data):
        if data.isspace(): return
        if self._is_distance and self._record:
            self._distance = data

def get_supported_locations(page, parser):
    """
    Returns the list of supported locations.
    """
    parser.feed(page.read())
    return parser._sources, parser._destinations

def parse_result_page(page, parser):
    parser.feed(page.read())
    return parser._distance

def get_source_destination_ids(sources, destinations, source, destination):
    fuzzy_sources = FuzzyDict(sources)
    fuzzy_destinations = FuzzyDict(destinations)
    return fuzzy_sources[source], fuzzy_destinations[destination]

def get_distance(source, destination):
    result_url = '%s/%s/and/%s' %(SITE_URL, source, destination)
    #print result_url

    try:
        result_page = urllib2.urlopen(result_url)
    except urllib2.URLError, msg:
        print 'Error: %s' %str(msg)
        sys.exit(1)

    return parse_result_page(result_page, DistanceFinder())

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print sys.modules['__main__'].__doc__
        sys.exit(1)

    source = sys.argv[1]
    destination = sys.argv[2]

    try:
        home_page = urllib2.urlopen(SITE_URL)
    except urllib2.URLError, msg:
        print 'Error: %s' %str(msg)
        sys.exit(1)

    sources, destinations = get_supported_locations(home_page, LocationFinder())
    source, destination = get_source_destination_ids(sources, destinations, source, destination)
    distance = get_distance(sources[source], destinations[destination])
    if distance:
        print '\n\tDistance from %s to %s is %s Kilometres\n' %(source, destination, distance)
    else:
        print '\n\tNo matching entry found in Database.\n'
