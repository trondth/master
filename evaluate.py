#r#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO
# Regne ut P/R/F både for hver enkelt expression og for alt samlet.
# Finne bug i spansets

import argparse
from itertools import izip

"""
1. Read iob-file, tuples - first col - last col, last col > 
"""

# 
# c( s, s' ) = |s \cap s'| / |s'|
# 
# 
# C( S, S' ) = Sum ( Sum ( c( s, s') ) )
# 
# P = C(S,Ŝ) / |Ŝ|
# R = C(Ŝ,S)/ |S|
# 
# 
# """                  

#from masters_project_config import *

class evaluate:

    def __init__(self, goldcol=-2, systemcol=-1, labels=['DSE', 'ESE', 'OSE']):
        #self.psum = 0    # spansetcoverage(gold, system)
        #self.pcount = 0  # len(system)
        #self.rsum = 0    # spansetcoverage(system, gold)
        #self.rcount = 0  # len(gold)
        self.labels = labels
        self.sums = {}
        self.counts = {}
        for label in self.labels:
            self.sums[label] = {'p': 0, 'r': 0}
            self.counts[label] = {'p': 0, 'r': 0}
        self.goldcol = goldcol
        self.systemcol = systemcol
        self.ln = 0

    def readsents(self, file, ignorefile=None):
        """
        Read sentences from test file, calculate c(s,s')s for each sentence
        according to Johansson, Moscitti (2013)

        (Sigma_sj(Sigma_s'k(c(sj,s'k)) kan regnes for hver setning, siden vi fraser vil
        være en del av en setning, og c(sj,s'k) vil være null ved forskjellige setninger)
        """
        f = open(file)
        setning = []
        ig_setning = []
        if ignorefile:
            ig_f = open(ignorefile)
            ig_f_start = True # if first line is blank, ignore
            for linenumber, line in enumerate(f):
                self.ln += 1
                if line[0] == '#':
                    pass # print line
                elif line == "\n":
                    ig_line = ig_f.readline()
                    #print "l'" + line + "'"
                    #print "i'" + ig_line + "'"
                    if ig_line != "\n":
                        #if ig_f_start:
                        #    print("first line")
                        #    ig_f_start = False
                        if ig_line != "":
                            print("ig_line er ikke newline, men {}. (l. {})".format(ig_line, linenumber))
                            raise Exception
                        else:
                            print("last line")
                    self.spansets(setning, ig_setning)
                    setning = []
                    ig_setning = []
                else:
                    ig_line = ig_f.readline()
                    setning.append(line)
                    ig_setning.append(ig_line)
            ig_f.close()
                    
        else:
            for line in f:
                self.ln += 1
                #print ln
                #print ",{},".format(line)
                if line == "\n":
                    # Setning ferdig, behandle den
                    #print "############\n{}\n\n".format(setning)
                    self.spansets(setning)
                    setning = []
                elif line[0] == '#':
                    tmp = 0 # print line
                else:
                    setning.append(line)
        f.close()
        if ignorefile:
            self.spansets(setning, ig_setning)
        else:
            self.spansets(setning)

    def spansets(self, setning, ig_setning=None):
        """
        (for each sentence:
        Adds to self.sums and self.counts for each label in self.labels
        # c( s, s' ) = |s \cap s'| / |s'|

        Summeres for hver setning:
        # C( S, S' ) = Sum ( Sum ( c( s, s') ) )

        Regnes ut for hele filen til slutt:
        # P = C(S,Ŝ) / |Ŝ| 
        # R = C(Ŝ,S)/ |S|
        """
        goldspansets = {}
        goldspancur = False
        systemspansets = {}
        systemspancur = False
        lastlabel = ""
        for label in self.labels:
            goldspansets[label] = []
            systemspansets[label] = []
        goldlast = 'O'
        systemlast = 'O'
        goldcur = False
        systemcur = False
        if ig_setning:
            ig_len = len(ig_setning[0].split()) - 1
            if ig_len == 0:
                ig_setning = False
            else:
                ig_goldcur = [False]*ig_len
                ig_goldlast = ['O']*ig_len
                ig_goldspancur = [False]*ig_len
        for i, line in enumerate(setning):
            if ig_setning:
                ig_list = ig_setning[i].split()
                #print line
                #print ig_list
                for c, ig in enumerate(ig_list[1:]):
                    #print ig
                    ig_goldcur[c], savelast = self.processline(ig_goldspancur[c], ig, ig_goldlast[c], i, debug=False)
                    if savelast:
                        goldspansets[ig_goldlast[c][2:]].append(ig_goldspancur[c])
                    ig_goldspancur[c] = ig_goldcur[c]
                    ig_goldlast[c] = ig
            cur = line.split()
            gold = cur[self.goldcol]
            system = cur[self.systemcol]
            goldcur, savelast = self.processline(goldspancur, gold, goldlast, i)
            if savelast:
                goldspansets[goldlast[2:]].append(goldspancur)
            goldspancur = goldcur
            goldlast = gold
            systemcur, savelast = self.processline(systemspancur, system, systemlast, i)
            if savelast:
                #print "SAVE:\n{}\n".format(systemspancur)
                systemspansets[systemlast[2:]].append(systemspancur)
            systemspancur = systemcur
            systemlast = system
            # Last line ew span (ign

        # Clean up if span ends on last token (line) in sentence
        if goldcur:
            goldspansets[gold[2:]].append(goldcur)
        if systemcur:
            systemspansets[system[2:]].append(systemcur)
        if ig_setning:
            for goldc in ig_goldcur:
                if ig != '_':
                    goldspansets[ig[2:]].append(goldc)
        
        #print "gold: ", [x[1] for x in goldspansets['ESE']]
        #print "sys:  ", [x[1] for x in systemspansets['ESE']]
        
        # Add to counters
        for label in self.labels:
            self.sums[label]['p'] += self.spansetcoverage(goldspansets[label],
                                                         systemspansets[label])
            self.sums[label]['r'] += self.spansetcoverage(systemspansets[label],
                                                         goldspansets[label])
            self.counts[label]['p'] += len(systemspansets[label]) 
            self.counts[label]['r'] += len(goldspansets[label])

        #print "p: {}".format(self.precision())
            #print "\n*********\nspansets(s/g):\n{}\n{}\n".format(systemspansets[label], goldspansets[label])
            #print "sums{}['p']: {}".format(label, self.sums[label]['p'])
            #print "c{}['p']: {}".format(label, self.counts[label]['p'])
        #self.psum += self.spansetcoverage(goldspans, systemspans)
        #self.pcount += len(systemspans)
        #self.rsum += self.spansetcoverage(systemspans, goldspans)
        #self.rcount += len(goldspans)

    def processline(self, spancur, cur, last, i, debug=False):
        """
        If line is a part of span, return type of span, else 
        """
        # if cur/last is _, this is a ignore-file, we will treat lines like these as outside
        if debug:
            print spancur, cur, last, i
        if cur == '_':
            cur = 'O'
        if last == '_':
            last = 'O'
        # Cur I, last B, fortsett span, ikke avslutt
        # Cur I, last I, fortsatt span, ikke avslutt
        if cur[0] == 'I' and (last[0] == 'B' or last[0] == 'I'):
            # Sjekk om label er lik, hvis ikke ny label og avslutt 
            if cur[2:] == last[2:]:
                spancur[1].add(i)
                spancur[2][1] = i
                return spancur, False
            else:
                return (cur[2:], set([i]), [i,i]), True
        # Begge O - ikke gjør noe
        if cur == 'O' and last == 'O':
            return False, False
        # Cur O, last B eller I - avslutt span
        if cur == 'O' and last != 'O':
            return False, True
        # Cur B or I, last O, ny span, ikke avslutt
        if (cur[0] == 'B' or cur[0] == 'I') and last == 'O':
            return (cur[2:], set([i]), [i,i]), False
        # Cur B, last B or I, ny span, avslutt:
        if cur[0] == 'B' and last != 'O':
            return (cur[2:], set([i]), [i,i]), True
        # Feil
        print "FEIL", cur, last, i
        return False, False

#    def spansets(self, setning):
#        """
#        """
#        goldspans = []
#        goldcur = False
#        systemspans = []
#        systemcur = False
#        #print ""
#        for i, line in enumerate(setning):
#            #print line
#            tmp = line.split()
#            #print tmp
#            gold = tmp[self.goldcol]
#            system = tmp[self.systemcol]
#            #gold
#            #print gold[0]
#            if goldcur and (gold[0] == 'B' or gold[0] == 'O'):
#                #print "End of sequence: {}".format(goldcur)
#                goldspans.append(goldcur)
#                goldcur = False
#            if not goldcur and (gold[0] == 'B'):
#                #print "Start of sequence"
#                goldcur = gold[2:], set([i]), [i,i]
#            if goldcur and (gold[0] == 'I' and goldcur):
#                #print "In sequence"
#                goldcur[1].add(i)
#                goldcur[2][1] = i
#            #print "FEIL Gold:   {}".format(line)
#            #system
#            if systemcur and (system[0] == 'B' or system[0] == 'O'):
#                systemspans.append(systemcur)
#                systemcur = False
#            if not systemcur and (system[0] == 'B'):
#                systemcur = system[2:], set([i]), [i,i]
#            if systemcur and (system[0] == 'I' and systemcur):
#                systemcur[1].add(i)
#                systemcur[2][1] = i
#            #else:
#            # print "FEIL System: {}".format(line)
#                            
#        # goldcur > goldspans / system...
#        if goldcur:
#            goldspans.append(goldcur)
#        if systemcur:
#            systemspans.append(systemcur)
#    
#        print goldspans, "\nS:", systemspans
#        print "count", (len(goldspans), len(systemspans))
#        # add to sum/coun
#        self.psum += self.spansetcoverage(goldspans, systemspans)
#        self.pcount += len(systemspans)
#        self.rsum += self.spansetcoverage(systemspans, goldspans)
#        self.rcount += len(goldspans)

    def readspans(self, file):
        """
        Reads spans from training file
        """
        f = open(file)
        spans = []
        cur = False
        for i, line in enumerate(f):
            #print line
            tmp = line.split()
            if len(tmp) > 0:
                tmp = tmp[-1]
                if cur and (tmp[0] == 'B' or tmp[0] == 'O'):
                    spans.append(cur)
                    cur = False
                if tmp[-1:][0] != 'O':
                    if len(tmp) < 5:
                        # TODO: Snevre inn mer?
                        print "Feil: linje: {}, {}".format(i, tmp)#line)
                    elif not cur:
                        cur = tmp[2:], set([i]), [i, i]
                    elif tmp[0] == 'I' and tmp[2:] == cur[0]:
                        cur[1].add(i)
                        cur[2][1] = i
                    #else: ulike tags
        f.close()
        #print "{} spans".format(len(spans))
        return spans
    
    
    def spancoverage(self, span, spanprime):
        #print "span spanprime", span, spanprime
        if span[0] != spanprime[0]:
            return 0
        tmp = span[1] & spanprime[1]
        if tmp:
            #print "tmp", tmp
            #print "spanprime", spanprime
            #print float(len(tmp)) / len(spanprime[1])
            return float(len(tmp)) / len(spanprime[1])
        return 0
    
    def spansetcoverage(self, spanset, spansetprime):
        #print spanset
        #print spansetprime
        sum = 0.0
        #count = 0
        for spanprime in spansetprime:
            for span in spanset:
                # since list is sorted, we can break if spanprime# > span#
                #if span[2][1] < spanprime[2][0]:
                #    break
                sum += self.spancoverage(span, spanprime)
                #count += 1
                #print count, sum
        #print sum
        #print '###'
        return sum
    
#    def precision(self, gold, system):
#        return self.spansetcoverage(gold, system) / len(system)
#    
#    def recall(self, gold, system):
#        return self.spansetcoverage(system, gold) / len(gold)

#    def precision(self):
#        if self.pcount == 0:
#            return -1
#        return self.psum / self.pcount
#    
#    def recall(self):
#        if self.rcount == 0:
#            return -1
#        return self.rsum / self.rcount

    def precision(self, labels=False):
        if not labels:
            labels = self.labels
        count = 0
        sum = 0
        for label in labels:
            print "\nLabel: ", label
            print self.counts[label]
            print "S", self.sums[label]
            count += self.counts[label]['p']
            sum += self.sums[label]['p']
        if count == 0:
            return -1
        return sum / count
    
    def recall(self, labels=False):
        if not labels:
            labels = self.labels
        count = 0
        sum = 0
        for label in labels:
            #print "\nLabel: ", label
            #print self.counts[label]
            #print "S", self.sums[label]
            #print "c", count
            #print "s", sum
            count += self.counts[label]['r']
            sum += self.sums[label]['r']
        if count == 0:
            return -1
        return sum / count

    def fscore(self, p, r):
        return 2 * p * r / (p + r)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", dest="filename", metavar="FILE")
    parser.add_argument("-g", "--ignored", dest="ig_filename", metavar="FILE")
    parser.add_argument("--pylab", dest="interactive",
                        help="For interactive development",
                        action='store_true')
    parser.add_argument("--automagic", dest="interactive",
                        help="For interactive development",
                        action='store_true')
    args = parser.parse_args()
    e = evaluate(goldcol=-3, systemcol=-2)
    #t = e.readsents('/hom/trondth/master/out/2015-02-19-result.txt')
    #e = evaluate()
    #t = e.readsents('evaltest.txt')
    if args.interactive:
        print "interactive"
        e = evaluate()
        t = e.readsents('evaltest.txt', 'evaltest.txt-ignore')
        #t = e.readsents('evaltest-minimal.txt', 'evaltest-minimal.txt-ignore')
        #t = e.readsents('evaltest.txt')#, 'evaltest.txt-ignore')
        p = e.precision()
        r = e.recall()
        print "P: ", p
        print "R: ", r
        print "F: ", e.fscore(p, r)
    else:
        if not args.filename:
            raise RuntimeError("Missing argument")
        if args.ig_filename:
            t = e.readsents(args.filename, args.ig_filename)
        else:
            t = e.readsents(args.filename)
        #tg = e.readspans('test.txt')
        #t = e.spansets(testb.splitlines())
        print "lines: {}".format(e.ln)
        p = e.precision()
        r = e.recall()
        print "P: ", p
        print "R: ", r
        print "F: ", e.fscore(p, r)
