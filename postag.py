##!/usr/bin/env python
# -*- coding: utf-8 -*-

from masters_project_config import *
from subprocess import Popen, PIPE
from collections import namedtuple
import xml.etree.ElementTree as etree
import os
import sys

stanford_path = DATA_PREFIX + config.get('stanford', 'PATH')
stanford_binary = ['java', '-cp', 'stanford-postagger.jar']
stanford_options = ['edu.stanford.nlp.tagger.maxent.MaxentTagger', '-model', 'models/english-left3words-distsim.tagger',
                    #'-tokenize', 'false',
                    #'-sentenceDelimiter', 'newline',
                    #'-outputFormat', 'tsv',
                    '-outputFormat', 'inlineXML',
                    '-outputFormatOptions', 'lemmatize',
                    ]

resaalign_binary = [DATA_PREFIX + '/resa/src/resaalign', '-f', 'TAB' ]

class Postag:
    #java -cp stanford-postagger.jar edu.stanford.nlp.tagger.maxent.MaxentTagger -model models/english-left3words-distsim.tagger -textFile foo.txt -outputFormat tsv -tokenize true

    def generate_string(self, dic=None, lst=None):
        """
        TODO
        """
        tmp = ""
        if dic:
            for item in dic['token'].items():
                tmp += item[1][0] + ' '
        elif lst:
            for tup in lst:
                tmp += tup[0] + ' '
        return tmp

    def generate_sents_string(self, lst):
        """
        TODO
        """
        tmp = ""
        for sent in lst:
            for tup in sent:
                tmp += tup[0] + ' '
            tmp += '\n\n'
        return tmp

    def runstanford(self, token_string, doc=None, options=stanford_options):
        """
    #java -cp stanford-postagger.jar edu.stanford.nlp.tagger.maxent.MaxentTagger -model models/english-left3words-distsim.tagger -textFile foo.txt -outputFormat tsv -tokenize true
    #java -cp stanford-postagger.jar edu.stanford.nlp.tagger.maxent.MaxentTagger -model models/english-left3words-distsim.tagger -textFile foo.txt -outputFormat  -tokenize true

        @param token_string Tokenized 
        @type document string
        @return output string from repp
        """
        working_dir = os.getcwd()
        os.chdir(stanford_path)
        p_stanford = Popen(stanford_binary + stanford_options, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        #p_stanford.stdin.write("{} \n".format(token_string))
        #p_resa = Popen(resaalign_binary + ['-r', DATA_PREFIX + '/' + doc], stdin=p_stanford.stdout, stdout=PIPE)
        #p_stanford.stdout.close()
        os.chdir(working_dir)
        #return p_resa.communicate()
        #print token_string
        return p_stanford.communicate("{} \n".format(token_string))

    def pos_tag_dict(self, dic, tagger=runstanford):
        """
        """
        newdict = {}
        newdict['sent'] = dic['sent']
        newdict['token'] = OrderedDict()
        tokens = self.runstanford(self.generate_string(dic))
        #print tokens
        if len(tokens[0].split()) != len(dic['token']):
            print("FEIL")
        for item in tokens[0].split():
            tag = item.split('_')
            if len(dic['token']) > 0:
                dictitem = dic['token'].popitem()
            #print("D: {}".format(dictitem))
            #TODO - gjør om til namedtuple
            newval = {'token': dictitem[1][0],
                      'cstart': dictitem[1][1],
                      'cstop': dictitem[1][2],
                      'postag': tag[1]}
            newdict['token'][dictitem[0]] = newval

        return newdict

#    def pos_tag_sent_lst(self, lst, tagger=runstanford):
#        """
#        """
#        Tokeninfo = namedtuple('Token', 'token lemma slice postag')
#        newlst = []
#        tree = etree.fromstring(self.runstanford(self.generate_string(lst=lst))[0])
#        #print tree
#        for (i,c) in enumerate(tree[0]):
#            try:
#            #if len(lst) < i:# or c.text != lst[i][0]:# and len(c.text) < 3 or c.text[-3:] != 'RB-': # TODO Flere spesialting
#            #    if len(lst) < i:
#            #        print "FEIL: {} lst kortere enn i{}".format(c.text, i)
#            #    else:
#            #        print "FEIL: {} ulik {}".format(c.text, lst[i][0])
#            #    print "{}".format(c.attrib)
#                newval = Tokeninfo(c.text,
#                               c.attrib['lemma'],
#                               lst[i][1],
#                               c.attrib['pos'])
#                newlst.append(newval)
#            except:
#                print "FEIL parse.py: \n{}\n\n{}".format(lst, c.text)
#        return newlst

    def resaalign(self, tsv, doc):
        # TODO - setningene i fra mpqa må sorteres
        print DATA_PREFIX, doc
        p = Popen(resaalign_binary + ['-r', DATA_PREFIX + '/' + doc], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        
        return p.communicate(tsv)

    def pos_tag_sents_lst(self, lst, filename, tagger=runstanford):
        """
        For multiple sentences
        """
        Tokeninfo = namedtuple('Token', 'token lemma slice postag')
        newsentlst = []
        #list = self.runstanford(self.generate_sents_string(lst=lst), filename)[0]
        tree = etree.fromstring(self.runstanford(self.generate_sents_string(lst=lst))[0])
        tokens = ""
        for sent in tree:
            for token in sent:
                tokens += "{}\n".format(token.text.encode('utf-8'))
                #, token.attrib['lemma'], token.attrib['pos'])
        offsetpos = self.resaalign(tokens, filename)[0].splitlines()
        linenum = 0
        for sent in tree:
            newlst = []
            for token in sent:
                try:
                    offset = offsetpos[linenum].split()
                    newval = Tokeninfo(token.text,
                                   token.attrib['lemma'],
                                   slice(int(offset[0]),int(offset[1])),
                                   token.attrib['pos'])
                    newlst.append(newval)
                except:
                    print "FEIL parse.py: \n{}\n\n{}\n\n({})".format("lst[linenum]", token.text, linenum)
                linenum += 1
            newsentlst.append(newlst)
        return newsentlst

    def pos_tag_sentences_lst(self, lst, tagger=runstanford):
        """
        TODO
        """
        return_lst = []
        for item in lst:
            return_lst.append(self.pos_tag_sent_lst(item, tagger=tagger))
        return return_lst

    #for line in tokens[0]:
        
if __name__ == "__main__":
    #testdoc = "20020510/21.50.13-28912"
    testdoc = "database.mpqa.2.0/docs/20020510/21.50.13-28912"
    #testdoc = "database.mpqa.2.0/docs/20010630/00.48.42-17806"
    sents = t_mpqa.sentences_from_file(testdoc)
    t3 = t_tokenizer.runrepponsentences(sents)
    p = Postag()
    #tmp = p.pos_tag_sents_lst(t3, testdoc)
    #tmp = p.generate_string(lst=t3)
    #tmp = tuplefromrepp(
    
    #s = m.getmpqatuples(testdoc, 'sentence')
    #s = m.annotations_from_file(testdoc)
        #print s
