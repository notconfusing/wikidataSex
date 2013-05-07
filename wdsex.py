#!/usr/bin/python
# -*- coding: utf-8 -*-

#import os
#os.environ['PYWIKIBOT2_DIR'] = '/home/notconfusing/workspace/gender_wd/rewrite/pywikibot'
import pywikibot
from collections import defaultdict
import urllib2
import xml
import xml.etree.ElementTree as ET
import rdflib
import json

#some constants
CORE = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
VIAF = rdflib.URIRef("http://viaf.org")
LCCNConcept = rdflib.URIRef('http://viaf.org/viaf/sourceID/LC')
LCCNXMLPost = '.marcxml.xml'

#some custom exceptions for cleanliness
class noLCCNLink(Exception):
    pass
class noLCCNOpinion(Exception):
    pass
class noVIAFOpinion(Exception):
    pass


#log into wikidata
en_wikipedia = pywikibot.Site('en', 'wikipedia')
wikidata = en_wikipedia.data_repository()
if not wikidata.logged_in(): wikidata.login()

propertyMap = {'LCCN': 'P244',
             'VIAF':'P214',
             'sex': 'P21',
             'imported from':'P143'}

sexItemMap = {'Q6581097': 'male', 
               'Q6581072': 'female', 
               'Q1097630': 'intersex'}

sexMap = {'female': 'Q6581072',
         'male': 'Q6581097',
         'intersex' : 'Q1097630'}

#make the wikidatapagegenerators
sex_property_page = pywikibot.ItemPage(wikidata, 'Property:' + propertyMap['sex'])
viaf_property_page = pywikibot.ItemPage(wikidata, 'Property:' + propertyMap['VIAF'])

pages_with_sex = sex_property_page.getReferences(total=10000)
pages_with_viaf = viaf_property_page.getReferences(total=1000)

#cases of interest
try:
    casesJSON = open('cases.JSON')
    cases = json.load(casesJSON)
    casesJSON.close()
except IOError:
    cases = {'prevtouched' : 0, 'seen' : 0, 'lccnnuances': [], 
             'wdnotviaf': 0, 'viafnotwd': 0, 'wdviafagree': 0, 'wdviafdisagree': 0, 
             'viafmale': 0, 'viaffemale': 0, 'wdmale':0, 'wdfemale' : 0, 'wdintersex': 0 }
    
def savecases():
    casesJSON = open('cases.JSON', 'w')
    json.dump(cases, casesJSON, indent=4)
    casesJSON.close()

#the current gerenator returns type Page, and we need ItemPage
def ItemPageGenerator(gen):
 for page in gen:
     yield pywikibot.ItemPage(page.site.data_repository(), page.title())
     
pages_with_sex = ItemPageGenerator(pages_with_sex)
pages_with_viaf = ItemPageGenerator(pages_with_viaf)

#the semantic web crawling helpers

#the viaf rdf miner
def findLCCNLink(rdfgraph):
    for s,p,o in rdfgraph:
        if s.startswith(LCCNConcept):
            if p == CORE.exactMatch:
                LCCNLink = o
                return LCCNLink
    raise noLCCNLink

#the lccn searcher
def getLCCNOpinion(LCCNLink):
    '''Returns our datatype for sex, a list of dicts who have required key 'sex', optional keys 'start' and 'transition' or an empty list'''
    opinion = list()
    lccnurl = LCCNLink + LCCNXMLPost
    marc_xml_string = urllib2.urlopen(lccnurl).read()
    root = ET.fromstring(marc_xml_string)
    ET.register_namespace('http://www.loc.gov/MARC21/slim','')
    for child in root:
        if child.tag == '{http://www.loc.gov/MARC21/slim}datafield':
            datafield = child
            datafield_attrib = child.attrib
            if datafield_attrib['tag'] == '375':
                opinion.append(dict())
                for subfield in datafield:
                    for ast in ['a','s','t']:
                        if subfield.attrib['code'] == ast:
                            opinion[-1][ast] = subfield.text          
    #opinion could be Empty List
    if not opinion:
        raise noLCCNOpinion
    return opinion

def getVIAFOpinionFromXML(marcxmlurl):
    '''Returns a sex, or none if none exists'''
    marc_xml_string = urllib2.urlopen(marcxmlurl).read()
    try:
        root = ET.fromstring(marc_xml_string)
    except ET.ParseError:
        print marc_xml_string
        raise noVIAFOpinion
    ET.register_namespace('http://www.loc.gov/MARC21/slim','')
    for child in root:
        if child.tag == '{http://www.loc.gov/MARC21/slim}datafield':
            datafield = child
            datafield_attrib = child.attrib
            if datafield_attrib['tag'] == '375':
                for subfield in datafield:
                    if subfield.attrib['code'] == 'a':
                        return subfield.text
    #nothing was found
    raise noVIAFOpinion


def getviafOpinion(viafnum):
    marcxmlurl = 'http://viaf.org/viaf/'+viafnum+'/marc21.xml'
    try:
        viafOpinion = getVIAFOpinionFromXML(marcxmlurl)
    except noVIAFOpinion:
        viafOpinion = None
    return viafOpinion

def getlccnOpinion(viafnum):
    xmlurl = 'http://viaf.org/viaf'+viafnum +'/rdf.xml'
    rdfgraph=rdflib.Graph()
    try:
        rdfgraph.load(xmlurl)
    except (xml.sax._exceptions.SAXParseException, urllib2.HTTPError) as e:
        print 'xml or url error'
        print e
        lccnOpinion = None
        return lccnOpinion
    try: 
        LCCNLink = findLCCNLink(rdfgraph)
        lccnOpinion = getLCCNOpinion(LCCNLink)
    except (noLCCNLink, noLCCNOpinion) as e:
        lccnOpinion = None
        return lccnOpinion
    
    return lccnOpinion


def mostInformative(viafOpinions):
    '''takes a list of viafOpinions. 
    returns a viafOpinion, which has more sex data than the other, or the first one if both equal'''
    return viafOpinion

def determineCase(pageTitle, wikidataOpinion, lccnOpinion, viafOpinion):
    cases['seen'] += 1
    #normalize viaf
    if viafOpinion == 'unknown': 
        viafOpinion = None
    #does lccn have transitioning dates
    if lccnOpinion:
        if len(lccnOpinion) > 1 or len(lccnOpinion[0].keys()) > 1:
            cases['lccnnuances'].append(pageTitle)
    if wikidataOpinion:
        wdkey = 'wd' + wikidataOpinion
        cases[wdkey] += 1
        if not viafOpinion:
            cases['wdnotviaf'] += 1
    if viafOpinion:
        viafkey = 'viaf' + viafOpinion
        cases[viafkey] += 1
        if not wikidataOpinion:
            cases['viafnotwd'] += 1
    if wikidataOpinion and viafOpinion:
        if wikidataOpinion == viafOpinion:
            cases['wdviafagree'] += 1
        else:
            cases['wdviafdisagree'] += 1

def genSexData():
    seen = 0
    for page in pages_with_viaf:
        seen += 1
        if cases['prevtouched'] >= seen:
            continue
        wikidataOpinion = None
        # a list of result for possibly many viaf nums whic we'll later pick one of.
        viafnums = list()
        print 'page: ', page 
        try:
            page_parts = page.get()
        except pywikibot.data.api.APIError as err:
            print err.code
            print err.info
        for claim_list in page_parts['claims'].itervalues():
            for claim in claim_list:
                if claim.id == 'p214':
                    viafnums.append(claim.target)
                if claim.id == 'p21':
                    #under the current implementation sex is supposed to be single-valued, i'm actually upset about this and wrote so on the talk page, but until then, sigh.
                    if not wikidataOpinion:
                        wikidataOpinion = sexItemDict[claim.target.title()]
                    #what if there's a better one that has a source
                    elif claim.sources:
                        wikidataOpinion = sexItemDict[claim.target.title()]
        lccnOpinions = [getlccnOpinion(viafnum) for viafnum in viafnums]
        viafOpinions = [getviafOpinion(viafnum) for viafnum in viafnums]
        lccnOpinion = mostInformative(lccnOpinions)
        viafOpinion = mostInformative(viafOpinons)                                 
        determineCase(page.title(), wikidataOpinion, lccnOpinion, viafOpinion) 
        #print ' wd: ', wikidataOpinion, ' lc: ', lccnOpinion, ' viaf: ', viafOpinion
        cases['prevtouched'] = seen
        savecases()

genSexData()