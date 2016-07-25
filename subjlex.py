##!/usr/bin/env python
# -*- coding: utf-8 -*-

from masters_project_config import *
from subprocess import Popen, PIPE
from collections import namedtuple
import xml.etree.ElementTree as etree
import re
import os
import sys

#subjlex_path = DATA_PREFIX + config.get('subjlex', 'PATH')
subjlex_path = DATA_PREFIX + '/unitn_subjexpr_source-111108/mpqa/subjlex/subjclueslen1-HLTEMNLP05.tff'
subjlex_re = re.compile(r'=(\S*)')

class Subjlex:

    def __init__(self):
        self.subjlex = {}
        Subjlextup = namedtuple('Subjlextup', 'type len pos1 stemmed1 priorpolarity')
        f = open(subjlex_path)
        for line in f:
            tup = tuple(subjlex_re.findall(line))
            if len(tup) == 6:
                if tup[2] not in self.subjlex:
                    self.subjlex[tup[2]] = {}
                self.subjlex[tup[2]][tup[3]] = (Subjlextup(tup[0], tup[1], tup[3], tup[4], tup[5]))
            elif len(tup) > 6:
                pass
                # To typer feil i leksikonet:
                #if tup[2].isdigit():
                #    # ('strongsubj', '1', '1', 'falter', 'verb', 'y', 'negative') - ekstra '1'
                #    if tup[3] not in self.subjlex:
                #        self.subjlex[tup[3]] = {}
                #    self.subjlex[tup[3]][4].append(Subjlextup(tup[0], tup[1], tup[4], tup[5], tup[6]))
                #else:
                #    # negative og strongneg som element 5 og 6
                #    if tup[2] not in self.subjlex:
                #        self.subjlex[tup[2]] = {}
                #    self.subjlex[tup[2]][tup[3]] = Subjlextup(tup[0], tup[1], tup[3], tup[4], tup[5])
            else:
                print "TODO FEIL: {}".format(tup)

    def getsubj(self, t):
        """
        TODO
        """
        items = False
        if t.lemma.lower() in self.subjlex:
            items = self.subjlex[t.lemma.lower()]
        elif t.token.lower() in self.subjlex:
            items = self.subjlex[t.token.lower()]
        if items:
            item = self.poscompare(t.postag, items)
            if item:
                try:
                    if item.type == 'weaksubj':
                        return 'weak/' + item.priorpolarity[0:2]
                    elif item.type == 'strongsubj':
                        return 'strong/' + item.priorpolarity[0:2]
                except:
                    print "KEY ERROR: {}".format(t)
        return '-'

    def poscompare(self, tag, items):
        """
        @return item if pos-tag from lex correspondent with pos from token.
        """
        if 'anypos' in items:
            return items['anypos']
        if tag[0] == 'N' and 'noun' in items:
            return items['noun']
        if tag[0] == 'J' and 'adj' in items:
            return items['adj']
        if tag[0] == 'V' and 'verb' in items:
            return items['verb']
        if tag[:2] == 'RB' and 'adverb' in items:
            return items['adverb']
        else:
            return False

    def getsubj_key(self, t):
        """
        Not in use
        """
        key = None
        if t.lemma.lower() in self.subjlex:
            key = t.lemma.lower()
        elif t.token.lower() in self.subjlex:
            key = t.token.lower()
        if key:
            try:
                if self.subjlex[key].type == 'weaksubj':
                    return 'weak/' + self.subjlex[key].priorpolarity[0:2]
                elif self.subjlex[key].type == 'strongsubj':
                    return 'strong/' + self.subjlex[key].priorpolarity[0:2]
            except:
                print "KEY ERROR: {}".format(t)
        return '-'

    def getsubj_lst(self, lst, Tup=None):
        """
        TODO
        """
        if not Tup:
            Tup = namedtuple('Tup', 'token lemma slice postag subj')
        return_lst = []
        for t in lst:
            if t.lemma in self.subjlex or t.token in self.subjlex:
                if self.subjlex[t.lemma].type == 'weaksubj':
                    tmp = 'weak/' + self.subjlex[t.lemma].priorpolarity[0:2]
                elif self.Subjlex[t.lemma].type == 'strongsubj':
                    tmp = 'strong/' + self.subjlex[t.lemma].priorpolarity[0:2]
                return_lst.append(Tup(t.token, t.lemma, t.slice, t.postag, tmp))
            else:
                return_lst.append(Tup(t.token, t.lemma, t.slice, t.postag, '-'))
        return return_lst

if __name__ == "__main__":
    Tokeninfo = namedtuple('Token', 'token lemma slice postag')
    s = Subjlex()
    print s.getsubj(Tokeninfo('Terrorism',
                   'Terrorism',
                   slice(1,2),
                   'NN'))
    print s.getsubj(Tokeninfo('Terrorism',
                   'Terrorism',
                   slice(1,2),
                   'TEST'))
