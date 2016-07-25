import ast
import os
import random
import re
from collections import OrderedDict
from future_builtins import zip
import shlex
from masters_project_config import *

def pairwise(iterable):
    """
    @param iterable: List or other iterable
    @return: List of tuples
    """
    a = iter(iterable)
    return zip(a, a)

class MPQA:

    re_attr = re.compile(r'("[^"]*"|[\w-]+)')
    
    def __init__(self, name="", mpqa_root=DATA_PREFIX):
        self.docs = OrderedDict({})
        self.name = name
        self.mpqa_root = mpqa_root
        if self.mpqa_root[:-1] != '/':
            self.mpqa_root += '/'

    def annotations_from_file(self, document):
        """
        Returns list with sentence objects from a gatesentences.mpqa.2.0-file.

        @param document: String refering to unique doc, example: 20010927/23.18.15-25073
        @return: List of sentence objects.
        """
        annotations = []
        f = file(self.mpqa_root + document, 'r')
        tmp = f.read()
        f.close()
        for tuple in self.getmpqatuples(document, 'annotations'):
            annotations.append((tuple, tmp[tuple[1]]))
        annotations.sort(key=lambda x: (x[1][1].start))
        return annotations
    
    def annotation_tuples_from_file(self, document):
        """
        Returns list of tuples from a gateman.mpqa.2.0-file, sorted on start positions.

        @param document: String refering to unique doc, example: 20010927/23.18.15-25073
        @return: List of tuples from annotation file.
        """
        annotations = []
        f = file(self.mpqa_root + document, 'r')
        tmp = f.read()
        f.close()
        for tuple in self.getmpqatuples(document, 'annotations'):
            annotations.append(tuple)
        #print annotations
        annotations.sort(key=lambda x: (x[1].start))
        #print annotations
        return annotations

    def sentences_from_file(self, document):
        """
        Returns list with sentence objects from a gatesentences.mpqa.2.0-file.
        
        @param document: String refering to unique doc, example: 20010927/23.18.15-25073
        @return: List of sentence objects.
        """
        sentences = []
        f = file(self.mpqa_root + document, 'r')
        tmp = f.read()
        f.close()
        for tuple in self.getmpqatuples(document, 'sentence'):
            sentences.append((tmp[tuple[1]],tuple))
        sentences.sort(key=lambda x: (x[1][1].start))
        return sentences

    def expandvariant(self, variant):
        if variant == 'sentence':
            return 'gatesentences.mpqa.2.0'
        if variant == 'annotations':
            return 'gateman.mpqa.lre.2.0'

    def tuplefrommpqa(self, line):
        """
        @param Line: from mpqatuples
        @return: Tuple with slice object as second element 
        """
        tmp = line.split(None, 4)
        tmp[1] = (lambda x: slice(int(x[0]), int(x[1])))(tmp[1].split(','))
        d = {}
        if len(tmp) > 4:
            #print tmp[4].split() # = (lambda x: slice(int(x[0]), int(x[1])))(tmp[1].split(','))
            tmp[4] = self.attributesfrommpqa(tmp[4])
        return tmp
    
    def attributesfrommpqa(self, attributes):
        """
        @param attributes: String with attributes
        @return: Dictionary with attributes
        """
        tmp = self.re_attr.findall(attributes)
        if len(tmp) % 2 != 0:
            print "Attribute string in MPQA file not wellformed. ({})".format(attributes)
        return {key: value.strip('"') for (key, value) in pairwise(tmp)} 

    re_docs = re.compile(r'/docs/')

    def getmpqatuples(self, document, variant):
        """
        @param document: String refering to unique doc, example: 20010927/23.18.15-25073
        @param variant:
        @return: List of 5-tuples from data in the MPQA-document
        """
        variant = self.expandvariant(variant)
        tuples = []
        f = file(self.mpqa_root +  self.re_docs.sub(r'/man_anns/', document) + '/' + variant, 'r')
        for line in f:
            if line[0] != '#':
                tuples.append(self.tuplefrommpqa(line))
        f.close()
        return tuples
            
if __name__ == "__main__":
    m = MPQA("Foo")
    #testdoc = "database.mpqa.2.0/docs/20020510/21.50.13-28912"
    #testdoc = "database.mpqa.2.0/docs/20010630/00.48.42-17806"
    #testdoc = 'database.mpqa.2.0/docs/20020314/20.23.54-19638'
    #testdoc = 'database.mpqa.2.0/docs/ula/20000410_nyt-NEW'
    #testdoc = 'database.mpqa.2.0/docs/ula/20000815_AFP_ARB.0084.IBM-HA-NEW'
    testdoc = 'database.mpqa.2.0/docs/20020315/20.42.26-19148'
    #testdoc = 'database.mpqa.2.0/docs/20020331/21.09.25-22686'

    s = m.getmpqatuples(testdoc, 'sentence')
    s2 = m.annotation_tuples_from_file(testdoc)
    #s = m.sentences_from_file(testdoc)
    #print s
    
    
