##!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict

from masters_project_config import *
from subprocess import Popen, PIPE, STDOUT
import re

tokenizer_binary = DATA_PREFIX + '/repp/src/repp'
#tokenizer_options = ['-c', DATA_PREFIX + '/repp/erg/repp.set']
tokenizer_options = ['-c', DATA_PREFIX + '/repp/erg/repp.set', '--format', 'triple']
resaalign_binary = DATA_PREFIX + '/resa/src/resaalign'

#[rdridan@sh repp]$ echo 'foo, (bar), ... baz!' | ./src/repp -c
#./erg/repp.set --format offsets
#<0:3> foo
#<3:4> ,
#<5:6> (
#<6:9> bar
#<9:10> )
#<10:11> , 
#<12:16> …
#<16:19> baz
#<19:20> !


#~/master/repp/erg/repp.set --format offsets
#d = subprocess.call(tokenizer_binary, '-c ' + DATA_PREFIX + '/database.mpqa.2.0/docs/' + testdoc )
#f = '-c ' + DATA_PREFIX + '/database.mpqa.2.0/' + testdoc 

class Tokenize:

    #def __init__(self,


    #TODO sett utenfor klasse
    triple_re = re.compile(r'\((\d*)\D*(\d*), (.*)\)')

    def runrepponsentences(self, sentences, return_list=None):
        """
        @param sentences List of tuples with raw sentence as 1 member and tuple with slice as second
        @type sentences list
        @param return_list
        @return list of tuples - tokens, slices
        """
        if not return_list:
            return_lst = []
        for sent in sentences:
            token_lst = []
            #print sent
            offset = sent[1][1].start
            p_repp = Popen([tokenizer_binary] + tokenizer_options, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            tuples = p_repp.communicate(input=sent[0]+'\n')
            #print
            for tp in tuples[0][:-1].splitlines():
                if tp != "":
                    try:
                        t = self.triple_re.match(tp).groups()
                        t_slice = slice(int(t[0]) + offset, int(t[1]) + offset)
                        t_token = t[2]
                        #print "...{}-{}".format(t_token, t_slice)
                        token_lst.append((t_token, t_slice))
                    except:
                        print "FEIL repp.py: t: {}".format(tp)
            return_lst.append(token_lst)
        return return_lst

    def runrepp(self, document):
        """
        @param document MPQA document id
        @type document string
        @return output string from repp
        """
        doc_full_path = DATA_PREFIX + '/' + document
        args = tokenizer_options + [doc_full_path ]
        p_repp = Popen([tokenizer_binary] + args, stdout=PIPE)
        p_resa = Popen([resaalign_binary, '-r', doc_full_path], stdin=p_repp.stdout, stdout=PIPE)
        p_repp.stdout.close()
        return p_resa.communicate()[0]

    def tuplefromrepp(self, reppoutput):
        """
        @param reppoutput Output from repp/resa
        @type reppoutput string
        @return dictionary - slices and tokens
        """
        d = {'sent': OrderedDict(),
             'token': OrderedDict()}
        for line in reppoutput.splitlines():
            cols = line.split('\t')
            #print cols
            if len(cols) > 2:
                if cols[2] == 'SENT':
                    value = (int(cols[0]), int(cols[1]))
                    d['sent'][cols[0]] = value
                elif cols[2] == 'TOK':
                    #value = slice(int(cols[0]), int(cols[1]))
                    token = cols[3][1:]
                    value = (token, int(cols[0]), int(cols[1]))
                    d['token'][cols[0]] = value
                else:
                    print("Line: {} not added".format(line))
                    print line, cols[1], cols[2]
        return d

# output=`dmesg | grep hda`
## becomes
#p1 = Popen(["dmesg"], stdout=PIPE)
#p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
#p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
#output = p2.communicate()[0]       
    

if __name__ == "__main__":
    #testdoc = "20020510/21.50.13-28912"
    #testdoc = "database.mpqa.2.0/docs/20020510/21.50.13-28912"
    #database.mpqa.2.0/docs/20020314/20.23.54-19638
    #testdoc = "database.mpqa.2.0/docs/20010630/00.48.42-17806"
    t = Tokenize()
    t3 = t.runrepponsentences(s)
    #tmp = t.runrepp(testdoc)
    #t2 = t.tuplefromrepp(s)
    #tmp = tuplefromrepp(
    #s = m.getmpqatuples(testdoc, 'sentence')
    #s = m.annotations_from_file(testdoc)
        #print s
