# -*- coding: utf-8 -*-

import nltk
from collections import OrderedDict

def example_text_list(example_text):
    example_text_list = []
    for line in example_text.splitlines():
        if line != '':
            example_text_list.append(line.split())
            #print "|{}|".format(line)
    return example_text_list

class SeqLists:

    def __init__(self):
        self.fds = {}
        self.lsts = OrderedDict({'B-DSE': [],
                                 'B-ESE': [],
                                 'B-OSE': [],
                                 'I-DSE': [],
                                 'I-ESE': [],
                                 'I-OSE': [],
                                 'O': [],
                                 'FIRST-O': []})

    def read_str(self, str):
        last_tag = ''
        for line in str.splitlines():
            if line != '':
                cols = line.split()
                self.line_to_lst(cols, last_tag)
                last_tag = cols[-1]

    def read_file(self, file):
        """
        Reads iob2 file to in to lists

        @param file Filename
        """
        last_tag = ''
        f = open(file)
        for line in f:
            #print "|{}|".format(line)
            if line != '\n':
                cols = line.split()
                self.line_to_lst(cols, last_tag)
                last_tag = cols[-1]
        f.close()

    def line_to_lst(self, cols, last_tag):
        if cols[-1] == 'B-DSE':
            self.lsts['B-DSE'].append(cols)
        elif cols[-1] == 'B-ESE':
            self.lsts['B-ESE'].append(cols)
        elif cols[-1] == 'B-OSE':
            self.lsts['B-OSE'].append(cols)
        elif cols[-1] == 'I-DSE':
            self.lsts['I-DSE'].append(cols)
        elif cols[-1] == 'I-ESE':
            self.lsts['I-ESE'].append(cols)
        elif cols[-1] == 'I-OSE':
            self.lsts['I-OSE'].append(cols)
        elif cols[-1] == 'O' and last_tag != 'O':
            self.lsts['FIRST-O'].append(cols)
        elif cols[-1] == 'O':
            self.lsts['O'].append(cols)
        else:
            print "Feil: {}".format(cols)

    def freqDists(self):
        for lst_t in self.lsts.items():
            print "list: ", lst
            if len(lst) > 0:
                cur = lst[0][-1]
                self.fds[cur] = self.freqDist(lst)
            
    def freqDist(self,lst):
        """
        @params lst lst
        """
        coln = len(lst[0])
        if coln != 5:
            print "Not implemented" # TODO
            return -1
        a = nltk.FreqDist(word for (word, lemma, pos, att, tag) in lst)
        b = nltk.FreqDist(lemma for (word, lemma, pos, att, tag) in lst)
        c = nltk.FreqDist(pos for (word, lemma, pos, att, tag) in lst)
        d = nltk.FreqDist(att for (word, lemma, pos, att, tag) in lst)
        return (a,b,c,d)

    def printFreqDist(self, label, fd, n=50):
        """
        Prints freqdist tab separated, for pasting into spreadsheet.

        @param label O, B-ESE ...
        @param fd Number TODO replace with dict.
        """
        for thing in self.fds[label][fd].most_common()[:n]:
            print("{}\t{}".format(thing[0], thing[1]))
    
#example_text_list_b-ese
         
#label_distribution = nltk.FreqDist(tag for (word, lemma, pos, att, tag) in example_text_list)
#pos_label_distribution = nltk.FreqDist((pos,tag) for (word, lemma, pos, att, tag) in example_text_list)

#print pos_label_distribution.items()

example_text = """The	the	DT	-	B-OSE
Kimberley	Kimberley	NNP	-	O
Provincial	Provincial	NNP	-	O
Hospital	Hospital	NNP	-	O
said	say	VBD	-	B-OSE
it	it	PRP	-	O
would	would	MD	weak/ne	B-DSE
probably	probably	RB	-	I-DSE
know	know	VB	strong/ne	I-DSE
by	by	IN	-	O
Tuesday	Tuesday	NNP	-	O
whether	whether	IN	-	O
one	one	CD	-	O
of	of	IN	-	O
its	its	PRP$	-	O
patients	patient	NNS	weak/po	O
had	have	VBD	-	O
Congo	Congo	NNP	-	O
Fever	fever	NN	weak/ne	O
.	.	.	-	O

Medical	Medical	NNP	-	O
Department	Department	NNP	-	O
head	head	NN	-	O
Dr	Dr	NNP	-	O
Hamid	Hamid	NNP	-	O
Saeed	Saeed	NNP	-	O
said	say	VBD	-	B-OSE
the	the	DT	-	O
patient	patient	NN	weak/po	O
's	's	POS	-	O
blood	blood	NN	weak/ne	O
had	have	VBD	-	O
been	be	VBN	-	O
sent	send	VBN	-	O
to	to	TO	-	O
the	the	DT	-	O
Institute	Institute	NNP	-	O
for	for	IN	-	O
Virology	Virology	NNP	-	O
in	in	IN	-	O
Johannesburg	Johannesburg	NNP	-	O
for	for	IN	-	O
analysis	analysis	NN	-	O
and	and	CC	-	O
the	the	DT	-	O
results	result	NNS	-	O
of	of	IN	-	O
the	the	DT	-	O
first	first	JJ	-	O
two	two	CD	-	O
sets	set	NNS	-	O
of	of	IN	-	O
tests	test	NNS	-	O
--	--	:	-	O
for	for	IN	-	O
illnesses	illness	NNS	weak/ne	O
other	other	JJ	-	O
than	than	IN	-	O
Congo	Congo	NNP	-	O
fever	fever	NN	weak/ne	O
--	--	:	-	O
arrived	arrive	VBD	-	O
back	back	RB	weak/po	O
on	on	IN	-	O
Monday	Monday	NNP	-	O
night	night	NN	-	O
and	and	CC	-	O
were	be	VBD	-	O
negative	negative	JJ	weak/ne	O
.	.	.	-	O
"""
    
if __name__ == '__main__':
    #example_text_list = example_text_list(example_text)
    sl = SeqLists()
    sl.read_str(example_text)
    #sl.read_file("../train.txt")
    sl.freqDists()
    sl.printFreqDist('O', 0)
    # Spesiell første felt
    #word_tag = nltk.FreqDist((word,tag) for (word, lemma, pos, att, tag) in example_text_list)

