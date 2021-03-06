#!/usr/bin/env python3
"""
Return the top similarity hits for query headwords

Prompts the user for query words.  The top n hits
from the similarity matrix are returned to STDOUT.

Requires package 'gensim'.

See README.txt for workflow details.
"""

import json
import os
import sys
import codecs
import unicodedata
import argparse
import re
import numpy as np
from progressbar import ProgressBar

from TessPy import tesslang

from gensim import corpora, models, similarities

# working directories on vagrant vm
basedir = "/vagrant"
tempdir = "/home/vagrant/dictionary-data"

#
# global variables
#

number = re.compile(r'[0-9]', re.U)

#
# functions
#

def load_ranks(lems, quiet):
    '''get the word ranks from Tesserae stoplist'''
    
    dict_rank = dict(parse_stop_list('la', '*', quiet), **parse_stop_list('grc', '*', quiet))
        
    array_rank = np.array([None] * len(lems))
    
    for i,lem in enumerate(lems):
        if lem in dict_rank:
            array_rank[i] = dict_rank[lem]
    
    return array_rank


def export_results(file, results, export_scores, quiet):
    '''write results to the output file'''
    
    file_output = open(file, 'w', encoding="utf_8")
    
    pr = ProgressBar(maxval = len(results))
    
    for rec in results:
        pr.update(pr.currval + 1)
        
        q, sims = rec
        row = [q]
        
        for pair in sims:
            r, score = pair
         
            if export_scores == 1:
                r = '{0}:{1}'.format(r, score)
            
            row.append(r)
        
        if file is not None:
            file.write(','.join(row) + '\n')
        else:
            print(','.join(row))
    
    pr.finish()


def parse_stop_list(lang, name, quiet):
    '''read frequency table'''
    
    # open stoplist file
    filename = None
    
    if name == '*':
        filename = os.path.join(basedir, "data", lang + '.stem.freq')
    else:
        filename = os.path.join(basedir, "data", name + '.freq_stop_stem')
  
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
    
    pr.update(len(head.encode('utf_8')))
    
    # read the individual token counts, divide by total
    
    score = dict()
    
    for n,line in enumerate(f):
        lemma, count = line.split('\t')
        
        lemma = tesslang.standardize(lang, lemma)
        lemma = number.sub('', lemma)
        
        score[lemma] = np.log(n+1)
        
        pr.update(pr.currval + len(line.encode('utf_8')))
    
    f.close()
    return score


def load_dict(filename, quiet):
    '''load a dictionary previously saved with pickle'''
    
    file_dict = os.path.join(tempdir, filename)
    
    if not quiet:
        print('Reading ' + file_dict)
    
    f = open(file_dict, "r", encoding="utf_8")
    
    data = json.load(f)
    
    f.close()
    
    return(data)


def is_greek(form):
    '''try to guess whether a word is greek'''
    
    for c in form:
        if ord(c) > 255:
            return(True)
    
    return(False)


def validate_arg_child(s):
    '''process argument to child flag, err if invalid format'''
    
    err_msg = None
    
    m = re.match("(\\d+):(\\d+)$", s)
    
    if m is None:
        err_msg = "Argument to --child must have format I:N, where I and N are integers and I <= N"
    else:
        child_id = int(m.group(1))
        nchildren = int(m.group(2))
        
        if child_id < 1:
            err_msg = "Child id must be greater than 0."
        elif child_id > nchildren:
            err_msg = "Child id can't exceed number of children"
    
    if err_msg is not None:
        raise argparse.ArgumentTypeError(err_msg)
    
    return (child_id, nchildren)


def main():
    #
    # check for options
    #
    parser = argparse.ArgumentParser(
        description='Query the headword similarities matrix')
    parser.add_argument('-q', '--query', metavar='LANG', type=str,
        choices=["greek", "latin"], default="greek",
        help = 'Language to translate from')
    parser.add_argument('-c', '--corpus', metavar='LANG', type=str,
        choices=["greek", "latin"], default="latin",
        help = 'Language to translate to')
    parser.add_argument('-o', '--output', metavar='FILE', type=str,
        default="trans.csv", help = 'Destination file')
    parser.add_argument('-t', '--topics', metavar='N', type=int, default=0,
        help = 'Reduce to N topics using LSI; 0=disabled')
    parser.add_argument('-r', '--results', metavar="N", type=int, default=2,
        help = 'Max number of results to produce for each query')
    parser.add_argument('-w', '--weight', metavar="F", type=float, default=0,
        help = 'Weight scores by inverse log-rank, coefficient F.'
                + ' Suggested range 0-1. Default is no weighting')
    parser.add_argument('--child', metavar="I:N", type=validate_arg_child,
        default = None, help = "This is child I of N, only do part of the work")
    parser.add_argument('--quiet', action='store_const', const=1,
        help = "Don't print status messages to stderr")
    
    opt = parser.parse_args()
        
    #
    # load data created by read_lexicon.py
    #
    
    # the index by word
    
    by_word = load_dict('lookup_word.json', opt.quiet)
    
    # the index by id
    
    by_id = np.array(load_dict('lookup_id.json', opt.quiet))
    
    # the corpus
    
    file_corpus = os.path.join(tempdir, 'defs_bow.json')
    
    if not opt.quiet:
        print('Loading corpus ' + file_corpus)
    
    corpus = load_dict(file_corpus, opt.quiet)
    
    #
    # use gensim to calculate similarities
    #
    #  NOTE: When you call similarities.Similarity with a value for the number
    # of similarities to calculate, the results are really different from what
    # you get if you leave that parameter out (i.e. calculate for all 
    # documents): with no number of sims, you get back a numpy array with as
    # many elements as there are documents, in an order corresponding to the
    # order of the documents in the corpus, where each element is the similarity
    # for the document in that position; if you specify a number of similarities
    # to return, then you get back a list of tuples, each tuple contains the
    # position of a document in the corpus and that document's similarity score.
    # These appear to be always in order of decreasing score.
    #
    # Older versions of this script expected the list of tuples, but didn't 
    # assume any order and re-ordered them by score. Now I've changed it to
    # expect the numpy array. Note that thanks to numpy you can use the array
    # like a vector in R. For example,
    #   sims = sims[filter]
    # subsets the sims array using another array, this time of boolean values.
    # Likewise, 
    #   sims -= np.absolute((rank[q_id] - rank[filter]) * opt.weight)
    # Subtracts from every element of sims the difference between one specific
    # rank, that of document q_id, and each element of array rank in turn.
    # The arrays rank and sims, each subset by filter, have the same number of
    # elements.
    #
    # I'm just writing this note to myself because I'm really new at this numpy
    # stuff and I might forget what I've done here otherwise. Delete this if
    # you like, later.
    
    # create dictionary
    
    if not opt.quiet:
        print('Creating dictionary')
    
    dictionary = corpora.Dictionary(corpus)
    
    # convert each sample to a bag of words
    
    if not opt.quiet:
        print('Converting each doc to bag-of-words')
    
    corpus = [dictionary.doc2bow(doc) for doc in corpus]
    
    # calculate tf-idf scores
    
    if not opt.quiet:
        print('Creating tf-idf model')
    
    tfidf = models.TfidfModel(corpus)
    
    if not opt.quiet:
        print('Transforming the corpus to tf-idf')
    
    corpus_tfidf = tfidf[corpus]
        
    # perform lsi transformation
    
    corpus_final = corpus_tfidf
    
    if opt.topics > 0:
        if not opt.quiet:
            print('Performing LSI with {0} topics'.format(opt.topics))
    
        lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=opt.topics)
        
        corpus_final = lsi[corpus_tfidf]
    
    # calculate similarities
    
    if not opt.quiet:
        print('Calculating similarities (please be patient)')
        
    dir_calc = os.path.join(tempdir, 'sims')
    
    index = similarities.Similarity(dir_calc, corpus_final, len(corpus_final))
    
    # consider frequency distribution
    
    rank = load_ranks(by_id, opt.quiet)
    
    # determine translation candidates, write output
    file_out = open(opt.output, "w", encoding="utf_8")
    
    if not opt.quiet:
        print('Writing translation candidates to {}'.format(opt.output))
    
    # optional filter by language
    filter = np.array([r is not None for r in rank])
    if (opt.corpus == "latin"):
        filter = filter & np.invert(np.array([is_greek(lem) for lem in by_id]))
    elif (opt.corpus == "greek"):
        filter = filter & np.array([is_greek(lem) for lem in by_id])
    
    # take each headword in turn as a query    
    pr = ProgressBar(maxval = len(by_word))
    
    results = []
      
    for q_id, sims in enumerate(index):
        pr.update(pr.currval + 1)
        q = by_id[q_id]
        
        if opt.query == "greek" and not is_greek(q):
            continue
        if opt.query == "latin" and is_greek(q):
            continue
        if rank[q_id] is None:
            continue
        
        # if child, only do every ith query
        if opt.child is not None:
            child_id, nchildren = opt.child
            
            if q_id % nchildren != child_id % nchildren:
                continue
        
        # add query word to filter
        filter[q_id] = False
      
        # apply filter
        sims = sims[filter]
    
        # apply distribution difference metric
        sims -= np.absolute((rank[q_id] - rank[filter]) * opt.weight)
    
        # add result words and sort by score
        sims = zip(by_id[np.arange(len(by_id))][filter], sims)
        sims = sorted(sims, key=lambda res: res[1], reverse=True)
    
        results = ["{0}:{1}".format(res, sim) for res, sim in sims[:opt.results]]
        file_out.write("{0},".format(q))
        file_out.write(",".join(results))
        file_out.write("\n")
    
    pr.finish()

    file_out.close()


if __name__ == '__main__':
    main()
