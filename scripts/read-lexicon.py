#!/usr/bin/env python3
"""
Parse the big XML dictionaries from Perseus 

This script looks for XML versions of Liddell-Scott-Jones and Lewis & Short, 
at data/grc.lexicon.xml and data/la.lexicon.xml, respectively.  It parses each
dictionary into headwords and English definitions.

"""

import sys
import re
import os
import os.path
import shutil
import codecs
import json
import argparse
import unicodedata
from progressbar import ProgressBar

from TessPy.tesserae import fs, url
from TessPy import tesslang

from stemming.porter2 import stem

basedir = "/vagrant"
tempdir = "/home/vagrant/dictionary-data"

#
# a collection of compiled regular expressions
#

class pat:
	'''Useful regular expressions'''
	
	# lexicon entry
	
	entry = re.compile(r'<entryFree [^>]*key="(.+?)"[^>]*>(.+?)</entryFree>')
	
	# XML nodes to omit
	
	stop = [
		re.compile(pat) for pat in [
			r'<cit>.*?</cit>',
			r'<bibl .+?>.*?</bibl>',
			r'<orth .+?>.*?</orth>',
			r'<etym .+?>.*?</etym>',
			r'<itype .+?>.*?</itype>',
			r'<pos .+?>.*?</pos>',
			r'<number .+?>.*?</number>',
			r'<gen .+?>.*?</gen>',
			r'<mood .+?>.*?</mood>',
			r'<case .+?>.*?</case>',
			r'<tns .+?>.*?</tns>',
			r'<per .+?>.*?</per>',
			r'<pron .+?>.*?</pron>',
			r'<date>.*?</date>',
			r'<usg .+?>.*?</usg>',
			r'<gramGrp .+?>.*?</gramGrp>'
		]
	]
	
	# language-specific regular expressions matching the parts of
	# dictionary entries that are English definitions of the headword
	
	definition = {
		'la': re.compile(r'<hi [^>]*rend="ital"[^>]*>(.+?)</hi>'),
		'grc': re.compile(r'<tr\b[^>]*>(.+?)</tr>')
	}
	
	# betacode greek tag
	# note that both dictionaries use <foreign lang="greek">
	# while neither uses <foreign> for any other language
	# (inside definitions, anyway)
	
	foreign = re.compile(r'<foreign lang="greek">(.+?)</foreign>')
	
	# stuff to remove from english entries
	
	clean = {
		'any': re.compile(r'\W+'),
		'la': re.compile(r'[^a-z]'),
		'grc': re.compile(r'[\^_]')
	}
	
	number = re.compile(r'[0-9]')


def mo_beta2uni(mo):
	'''A wrapper for tesslang.beta_to_uni that takes match objects'''
	
	return tesslang.beta_to_uni(mo.group(1))


def write_dict(defs, name, quiet):
	'''Save a copy of the dictionary in json format'''
	
	f = open(os.path.join(tempdir, name + '.json'), 'w', encoding="utf_8")
		
	if not quiet:
		print("Saving dictionary to {0}".format(f.name))
		
	json.dump(defs, f, ensure_ascii=False)
	
	f.close()


def read_dict(name, quiet):
	'''Load a copy of the dictionary in json format'''
	
	f = open(os.path.join(tempdir, name + '.json'), 'r', encoding="utf_8")
		
	if not quiet:
		print("Loading dictionary from {0}".format(f.name))
		
	defs = json.load(f)
	
	return defs


def parse_XML_dictionaries(langs, quiet):
    '''Create a dictionary of english translations for each lemma'''
    
    defs = dict()
    
    # process latin, greek lexica in turn
    
    for lang in langs:
        filename = os.path.join(basedir, 'data', lang + '.lexicon.xml')
        
        if not quiet:
            print('Reading lexicon {0}'.format(filename))
        
        pr = ProgressBar(maxval = os.stat(filename).st_size)
        
        try: 
            f = open(filename, "r", encoding="utf_8")
        except IOError as err:
            print("Can't read {0}: {1}".format(filename, str(err)))
            sys.exit(1)
        
        #
        # Each line in the lexicon is one entry.
        # Process one at a time to extract headword, definition.
        #
        
        for line in f:
            pr.update(pr.currval + len(line.encode('utf-8')))
            
            # skip lines that don't conform with the expected entry structure
            
            m = pat.entry.search(line)
            
            if m is None:
                continue
            
            lemma, entry = m.group(1, 2)
            
            # standardize the headword
            
            lemma = pat.clean[lang].sub('', lemma)
            lemma = pat.number.sub('', lemma)
            lemma = tesslang.standardize(lang, lemma)
            
            # remove elements on the stoplist
            
            for stop in pat.stop:
                entry = stop.sub('', entry)
            
            # transliterate betacode to unicode chars
            # in foreign tags
            
            entry = pat.foreign.sub(mo_beta2uni, entry)
            
            # extract strings marked as translations of the headword
            
            def_strings = pat.definition[lang].findall(entry)
            
            # drop empty defs
            
            def_strings = [d for d in def_strings if not d.isspace()]
            
            # skip lemmata for which no translation can be extracted
            
            if def_strings is None:
                continue
            
            if lemma in defs and defs[lemma] is not None:					
                defs[lemma].extend(def_strings)
            else:
                defs[lemma] = def_strings
        
        pr.finish()
    
    if not quiet:
        print('Read {0} entries'.format(len(defs)))
        print('Flattening entries with multiple definitions')
    
    pr = ProgressBar(maxval = len(defs))
    
    empty_keys = set()
    
    for lemma in defs:
        pr.update(pr.currval + 1)
        
        if defs[lemma] is None or defs[lemma] == []:
            empty_keys.add(lemma)
            continue
        
        defs[lemma] = '; '.join(defs[lemma])
    
    pr.finish()
    
    if not quiet:
        print('Lost {0} empty definitions'.format(len(empty_keys)))
    
    for k in empty_keys:
        del defs[k]
    
    return(defs)


def parse_stop_list(lang, name, quiet):
    '''read frequency table'''
    
    # open stoplist file
    
    filename = None
    
    if name == '*':
        filename = os.path.join(basedir, "data", lang + '.stem.freq')
    else:
        filename = os.path.join(basedir, name + '.freq_stop_stem')
    	
    if not quiet:
        print('Reading stoplist {0}'.format(filename))
    	
    pr = ProgressBar(maxval = os.stat(filename).st_size)
    
    try:
        f = open(filename, "r", encoding="utf_8")
    except IOError as err:
        print("Can't read {0}: {1}".format(filename, str(err)))
        sys.exit(1)
    
    # read stoplist header to get total token count
    
    head = f.readline()
    
    m = re.compile('#\s+count:\s+(\d+)').match(head)
    
    if m is None:
        print("Can't find header in {0}".format(filename))
        sys.exit(1)
    	
    total = int(m.group(1))
    
    pr.update(pr.currval + len(head.encode('utf-8')))
    
    # read the individual token counts, divide by total
    
    freq = dict()
    
    for line in f:
        
        lemma, count = line.split('\t')
        
        lemma = tesslang.standardize(lang, lemma)
        lemma = pat.number.sub('', lemma)
        
        freq[lemma] = float(count)/total
        
        pr.update(pr.currval + len(line.encode('utf-8')))
        
    pr.finish()
    
    return(freq)


def bag_of_words(defs, stem_flag, quiet):
    '''convert dictionary definitions into bags of words'''
    
    # convert to bag of words, count words
    
    if not quiet:
        print("Converting defs to bags of words")
    
    count = {}
    
    pr = ProgressBar(maxval = len(defs))
    
    empty_keys = set()
    
    for lemma in defs:
        pr.update(pr.currval + 1)
                
        defs[lemma] = [tesslang.standardize('any', w) 
            for w in pat.clean['any'].split(defs[lemma]) 
            if not w.isspace() and w != '']
        
        if stem_flag:
            defs[lemma] = [stem(w) for w in defs[lemma]]
        
        if len(defs[lemma]) > 0:
            for d in defs[lemma]:
                if d in count:
                    count[d] += 1
                else:
                    count[d] = 1
        else:
            empty_keys.add(lemma)    
    
    pr.finish()
    
    if not quiet:
        print("Removing hapax legomena")
    
    pr = ProgressBar(maxval = len(defs))
    
    for lemma in defs:
        pr.update(pr.currval + 1)
        
        defs[lemma] = [w for w in defs[lemma] if count[w] > 1]
        
        if defs[lemma] == []:
            empty_keys.add(lemma)
	
    pr.finish()
    
    if not quiet:
        print('Lost {0} empty definitions'.format(len(empty_keys)))
	
    for k in empty_keys:
        del defs[k]
    
    return(defs)


def build_corpus(defs, quiet):
    '''Create a "corpus" of the type expected by Gensim'''
    
    if not quiet:
        print('Generating Gensim-style corpus')
    
    pr = ProgressBar(maxval = len(defs))
    
    corpus = []
    
    for lemma in defs:
       	pr.update(pr.currval + 1)
       	
       	corpus.append(defs[lemma])
    
    pr.finish()
    
    return(corpus)


def make_index(defs, quiet):
    '''Create two look-up tables: one by id and one by headword'''
    
    if not quiet:
        print('Creating indices')
    
    by_word = {}
    by_id = []
    
    pr = ProgressBar(maxval = len(defs))
    
    for lemma in defs:
        pr.update(pr.currval + 1)
        
        by_id.append(lemma)
        by_word[lemma] = len(by_id) - 1
    
    pr.finish()
    
    return (by_word, by_id)


def main():
    #
    # check for options
    #
    
    parser = argparse.ArgumentParser(
   			description='Read dictionaries')
    parser.add_argument('-c', '--cache', action='store_const', const=1,
   			help='Use cached version of dictionaries')
    parser.add_argument('-s', '--stem', action='store_const', const=1,
   			help='Apply porter2 stemmer to definitions')
    parser.add_argument('-q', '--quiet', action='store_const', const=1,
   			help='Print less info')
    parser.add_argument('-m', '--match', action='store_const', const=1,
   			help = "Restrict candidates to Tesserae's stems")
    
    opt = parser.parse_args()
    quiet = opt.quiet
    
    # make sure working directory exists
    if os.path.isdir(tempdir):
        shutil.rmtree(tempdir)
    os.makedirs(tempdir)

    #
    # read the dictionaries
    #
    
    if opt.cache == 1:
        defs = read_dict('defs_full', opt.quiet)
    else:
        defs = parse_XML_dictionaries(['la', 'grc'], opt.quiet)
    
    if "" in defs:
        del defs[""]
    
    write_dict(defs, 'defs_full', opt.quiet)
    
    # convert to bag of words
    
    defs = bag_of_words(defs, opt.stem, opt.quiet)
    
    if opt.match:
        # read the Tesserae stoplist
        
        freq = dict(parse_stop_list('la', '*', opt.quiet), **parse_stop_list('grc', '*', opt.quiet))
        
        # limit synonym dictionary to members of stem dictionary
        
        print('restricting synonym dictionary to extisting stem index')
        
        lost_keys = []
        
        for lemma in defs:
            if lemma not in freq:
                lost_keys.append(lemma)
        
        for lemma in lost_keys:
            del defs[lemma]
        
    if not opt.quiet:
        print('{0} lemmas still have definitions'.format(len(defs)))
    
    # convert back into one string of defining words per lemma
    
    corpus = build_corpus(defs, opt.quiet)
    write_dict(corpus, 'defs_bow', opt.quiet)
    
    # create and save by-word and by-id lookup tables
    
    by_word, by_id = make_index(defs, opt.quiet)
    write_dict(by_word, 'lookup_word', opt.quiet)
    write_dict(by_id, 'lookup_id', opt.quiet)


if __name__ == '__main__':
    main()
