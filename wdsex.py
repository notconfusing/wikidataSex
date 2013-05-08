#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
os.environ['PYWIKIBOT2_DIR'] = '/home/kleinm/workspace/WikidataVIAFbot_branch'
import pywikibot
from collections import defaultdict
import urllib2
import xml
import xml.etree.ElementTree as ET
import rdflib
import json
import logging
logging.basicConfig(filename='logofwdsex.log',level=logging.DEBUG)

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

ItemMap = {'Q6581097': 'male', 
               'Q6581072': 'female', 
               'Q1097630': 'intersex'}

sexMap = {'female': 'Q6581072',
         'male': 'Q6581097',
         'intersex' : 'Q1097630',
         'VIAF': 'Q54919',
         'LCCN': 'Q620946',}

#make the wikidatapagegenerators
sex_property_page = pywikibot.ItemPage(wikidata, 'Property:' + propertyMap['sex'])
viaf_property_page = pywikibot.ItemPage(wikidata, 'Property:' + propertyMap['VIAF'])

pages_with_sex = sex_property_page.getReferences(total=10000)
pages_with_viaf = viaf_property_page.getReferences(total=1000000)

#cases of interest
try:
    casesJSON = open('cases.JSON')
    cases = json.load(casesJSON)
    casesJSON.close()
except IOError:
    cases = {'prevtouched' : 0, 'seen' : 0, 'lccnnuances': [], 
             'wdnotviaf': 0, 'viafnotwd': 0, 'wdviafagree': 0, 'wdviafdisagree': [], 
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
    try:
        marc_xml_string = urllib2.urlopen(marcxmlurl).read()
        root = ET.fromstring(marc_xml_string)
    except (ET.ParseError, urllib2.HTTPError, urllib2.URLError) as e:
        raise noVIAFOpinion
    ET.register_namespace('http://www.loc.gov/MARC21/slim','')
    for child in root:
        if child.tag == '{http://www.loc.gov/MARC21/slim}datafield':
            datafield = child
            datafield_attrib = child.attrib
            if datafield_attrib['tag'] == '375':
                for subfield in datafield:
                    if subfield.attrib['code'] == 'a':
                        if subfield.text == 'unknown':
                            return None
                        else:
                            return subfield.text
    #nothing was found
    raise noVIAFOpinion


def getviafOpinion(viafnum):
    viafOpinion = None
    if viafnum:
        marcxmlurl = 'http://viaf.org/viaf/'+viafnum+'/marc21.xml'
        try:
            viafOpinion = getVIAFOpinionFromXML(marcxmlurl)
        except noVIAFOpinion:
            return viafOpinion
    return viafOpinion

def getlccnOpinion(viafnum):
    lccnOpinion = None
    if viafnum:
        xmlurl = 'http://viaf.org/viaf/'+viafnum +'/rdf.xml'
        rdfgraph=rdflib.Graph()
        try:
            rdfgraph.load(xmlurl)
        except (xml.sax._exceptions.SAXParseException, urllib2.HTTPError) as e:
            print 'xml or url error'
            print e
            return lccnOpinion
        try: 
            LCCNLink = findLCCNLink(rdfgraph)
            lccnOpinion = getLCCNOpinion(LCCNLink)
        except (noLCCNLink, noLCCNOpinion, urllib2.HTTPError) as e:
            return lccnOpinion
    
    return lccnOpinion


def mostInformativeVIAF(viafOpinions, page):
    '''takes a list of viafOpinions. 
    returns a viafOpinion, which has more sex data than the other'''
    mostInformativeOpinion = None
    for viafOpinion in viafOpinions:
        #is there an opinion here?
        if viafOpinion:
            #is there a potentially competing opinion?
            if not mostInformativeOpinion:
                mostInformativeOpinion = viafOpinion
            #if there is already an opinion is it the same?
            elif mostInformativeOpinion == viafOpinion:
                continue
            else:
                #conflicting viaf, that's weird, lets log it
                logging.warning('conflicting sex for multiple viafs on %s', page.title())
                continue
    return mostInformativeOpinion

def mostInformativeLCCN(lccnOpinions, page):
    '''takes a list of lccnOpinions. 
    returns a viafOpinion, which has more sex data than the other, or the first one if both equal'''
    mostInformativeOpinion = None
    greatestLength = 0
    for lccnOpinion in lccnOpinions:
        if lccnOpinion:
            if len(lccnOpinion) > greatestLength:
                mostInformativeOpinion = lccnOpinion
    return mostInformativeOpinion

def addClaimWithSource(page, opinion):
    claimObj = pywikibot.Claim(site=wikidata, pid=propertyMap['sex'])
    sexPageValue = pywikibot.ItemPage(site=wikidata, title=sexMap[opinion])
    claimObj.setTarget(sexPageValue)
    
    page.addClaim(claimObj)
    print 'omg added'
    
    sourceObj = pywikibot.Claim(site=wikidata, pid=propertyMap['imported from'])
    VIAFPageValue = pywikibot.ItemPage(site=wikidata, title=sexMap['VIAF'])
    sourceObj.setTarget(VIAFPageValue)
    
    claimObj.addSource(sourceObj, bot=True)

def addSourceToClaim(claim):
    
    sourceObj = pywikibot.Claim(site=wikidata, pid=propertyMap['imported from'])
    VIAFPageValue = pywikibot.ItemPage(site=wikidata, title=sexMap['VIAF'])
    sourceObj.setTarget(VIAFPageValue)
    
    claim.addSource(sourceObj, bot=True)
    print 'omg added'
        

def determineCase(page, sexClaim, wikidataOpinion, lccnOpinion, viafOpinion):
    cases['seen'] += 1
    #does lccn have transitioning dates
    if lccnOpinion:
        if len(lccnOpinion) > 1 or len(lccnOpinion[0].keys()) > 1:
            cases['lccnnuances'].append(page.title())
            #we'er just going to log the complex cases for now, until we can add with qualifiers
            return
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
            #we're adding new data
            #addClaimWithSource(page, viafOpinion)
    if wikidataOpinion and viafOpinion:
        if wikidataOpinion == viafOpinion:
            cases['wdviafagree'] += 1
            #addSourceToClaim(sexClaim)
        else:
            cases['wdviafdisagree'].append(page.title())
            #addClaimWithSource(viafOpinion)

def genSexData():
    touched = 0
    for page in pages_with_viaf:
        touched += 1
        print touched
        if cases['prevtouched'] >= touched:
            continue
        wikidataOpinion = None
        # a list of result for possibly many viaf nums whic we'll later pick one of.
        viafnums = list()
        sexClaim = None
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
                    print 'viafvalue is: ',  claim.target
                    print type(claim.target)
                if claim.id == 'p21':
                    #under the current implementation sex is supposed to be single-valued, i'm actually upset about this and wrote so on the talk page, but until then, sigh.
                    if not wikidataOpinion:
                        #some sex values are unkown, like for jack the ripper
                        if claim.target:
                            wikidataOpinion = ItemMap[claim.target.title()]
                            sexClaim = claim
                    #what if there's a better one that has a source
                    elif claim.sources:
                        if claim.target:
                            wikidataOpinion = ItemMap[claim.target.title()]
                            sexClaim = claim
        print 'wikidataopinion: ', wikidataOpinion
        lccnOpinions = [getlccnOpinion(viafnum) for viafnum in viafnums]
        lccnOpinion = mostInformativeLCCN(lccnOpinions, page)
        print 'lccnopinions: ',  lccnOpinions, 'most informative: ', lccnOpinion
        viafOpinions = [getviafOpinion(viafnum) for viafnum in viafnums]
        viafOpinion = mostInformativeVIAF(viafOpinions, page)        
        print 'viafopinions: ',  viafOpinions, 'most informative: ', viafOpinion                  
        determineCase(page, sexClaim, wikidataOpinion, lccnOpinion, viafOpinion)
        #print ' wd: ', wikidataOpinion, ' lc: ', lccnOpinion, ' viaf: ', viafOpinion
        cases['prevtouched'] = touched
        savecases()

genSexData()