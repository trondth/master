##!/usr/bin/env python
# -*- coding: utf-8 -*-

from masters_project_config import *
from subprocess import Popen, PIPE
from collections import namedtuple
from collections import OrderedDict
import xml.etree.ElementTree as etree
import copy
import codecs
import os
import sys
import re
import json
import io
import pickle

import subjlex 
import repp    
import postag 
import mpqa  
import lth_srl
import bohnet_nivre

import argparse

# TODO - as class?

def createfile(filename="out.txt", testset=False, devset=True, opinionexp=True, opinionholder=False, doclistfile=False):
    """
    Runs pipeline and writes training file
    
    @param filename: Output filename, relative from DATA_PREFIX
    """
    if doclistfile:
        with open(DATA_PREFIX + doclistfile) as f:
            filelist = [line[:-1] for line in f]
    elif devset:
        if testset:
            with open(DATA_PREFIX + config.get('doclist', 'DEVPATH') +
                      '/' + config.get('doclist', 'DEVTESTSET')) as f:
                filelist = [line[:-1] for line in f]
        else:
            with open(DATA_PREFIX + config.get('doclist', 'DEVPATH') +
                      '/' + config.get('doclist', 'DEVTRAINSET')) as f:
                filelist = [line[:-1] for line in f]
    else:
        if testset:
            with open(DATA_PREFIX + config.get('doclist', 'PATH') +
                      '/' + config.get('doclist', 'TESTSET')) as f:
                filelist = [line[:-1] for line in f]
        else:
            with open(DATA_PREFIX + config.get('doclist', 'PATH') +
                      '/' + config.get('doclist', 'TRAINSET')) as f:
                filelist = [line[:-1] for line in f]
    if opinionexp:
        for file in filelist:
            print "FIL: {}".format(file)
            iob2str, ignored_exp_str = getopinionexp_iob2(file)
            if testset:
                with open(filename + '-ignore', 'a') as ign_f:
                    for line in ignored_exp_str:
                        ign_f.write(line.encode('utf-8'))
                                    #for (line, ignore_line) in zip(iob2str, ignored_exp_str):
            with open(filename, 'a') as f:
                for line in iob2str:
                    f.write(line.encode('utf-8'))
                    #if testset:
                    #    f.write(line.encode('utf-8')) 
                    #    ign_f.write(ignore_line.encode('utf-8'))
                    #    #f.write(lastcol_re.sub("", line).encode('utf-8')) # u'\u2019' # TODO - takler wapiti dette?
                    #else:
                    #    f.write(line.encode('utf-8')) 

    elif opinionholder:
        tmp = []
        for file in filelist:
            #print "FIL: {}".format(file)
            tmp.extend(getopinionholder(file))
            #break #TODO
        #with open(filename, 'w') as outfile:
        #    json.dump(tmp, outfile)
        #b = writeconll(tmp, DATA_PREFIX + "/out/tmp.conll")
        #lth = lth_srl.Lth_srl()
        #conlloutput = lth.run(data_prefix + "/out/tmp.conll")
        #c = readconlltolst(a, conlloutput)
        #d = getholdercandidates(c)
        return tmp

class PickleEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (list, dict, str, unicode, int, float, bool, type(None))):
            return JSONEncoder.default(self, obj)
        return {'_pickle_object': pickle.dumps(obj)}

def pickle_object(dct):
    if '_pickle_object' in dct:
        return pickle.loads(str(dct['_pickle_object']))
    return dct

class SliceEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, slice):
            return {'start': str(obj.start), 'stop': str(obj.stop)}
        return json.JSONEncoder.default(self, obj)

def json_slice(dct):
    #print "slice"
    if ('slice' in dct):
        str = dct['slice']
        if isinstance(str, basestring) and str[:6] == 'slice(':
            #print "str/unicode"
            str = str[6:-1].split(',')
            dct['slice'] = slice(int(str[0]), int(str[1]))
        elif ('start' in dct['slice'] and
        'stop' in dct['slice']):
            #start = dct['slice']['start']
            tmp = slice(int(dct['slice']['start']), int(dct['slice']['stop']))
            dct['slice'] = tmp
    return dct

def dump_jsonfile(lst, filename):
    """
    Dumps list of sents to jsonfile
    """
    if os.path.exists(filename):
        overwrite_ok = raw_input('File exists. Overwrite? (y/N)')
        if overwrite_ok != 'y' and overwrite_ok != 'j':
            return -1
    f = open(filename, 'w')
    json.dump(lst, f, cls=PickleEncoder)
    f.close()
    
def read_jsonfile(filename, object_hook=pickle_object): #json_slice):#pickle_object):
    """
    @return lst of sents
    """
    with open(filename, 'r') as file:
        lst = json.load(file, object_hook=object_hook)
    return lst

#class SliceDecoder(json.JSONDecoder):
#    def decode(self, json_string):
#        default_obj = super(TemplateJSONDecoder, self).decode(json_string)
#        if ('slice' in default_obj and
#            'start' in default_obj['slice'] and
#            'stop' in default_obj['start']):
#                return slice(default_obj['start'], default_obj['stop'])
#        return default_obj
   
def find_expr_heads(lst):
    """
    For each expression, find token with head outside expression span.
    Make list of expressions with more than one token with head outside span.
    """
    sent_exp_head_dict = []
    for sent in lst:
        expression_head_dict = OrderedDict()
        for i, token in enumerate(sent):
            token['nr'] = i+1
            gate_line_ids = _is_part_of_expression(token)
            if gate_line_ids:
                for line_id in gate_line_ids:
                    if not _is_part_of_expression(sent[int(token['head'])-1], gate_line_id=line_id):
                        #print token
                        if 'line_id' in expression_head_dict:
                            expression_head_dict[line_id].append(token)
                        else:
                            expression_head_dict[line_id] = [token]
        sent_exp_head_dict.append(expression_head_dict)
    return sent_exp_head_dict



def _is_part_of_expression(token, gate_line_id=False):
    expression_lst = []
    for gate in token['GATE']:
        if gate_line_id:
            if gate['line_id'] == gate_line_id:
                return True
        else:
            if (gate['ann_type'] == 'GATE_objective-speech-event' or
                gate['ann_type'] == 'GATE_expressive-subjectivity' or
                gate['ann_type'] == 'GATE_direct-subjective'):
                expression_lst.extend(gate['line_id'])
    if expression_lst:
        return expression_lst
    return False
        

def find_possible_paths(lst):
    """
    For each token in sent, find path to all other tokens in sent.
    """
    pass
    

def printopinionexpression(lst, ignorelst=['GATE_attitude', 'GATE_inside', 'GATE_target']):
    for sent in lst:
        for i, token in enumerate(sent):
            #print token
            prstr = "{}\t".format(i)
            prstr = "{}\t".format(token['form'])
            if 'head' in token:
                prstr += "{}\t".format(token['head'])
            prstr += "{}".format(token['pos'])
            if 'holder_candidate' in token:
                prstr += "[C]"
            for gate in token['GATE']:
                #print gate
                #for gate in gates:
                if gate['ann_type'] not in ignorelst and gate['slice'].start - gate['slice'].stop != 0:
                    prstr += "\t[{}-{}]".format(gate['slice'].start, gate['slice'].stop)
                    prstr += "{}".format(gate['ann_type'])
                    if 'nested-source' in gate: 
                        prstr += '({})'.format(gate['nested-source'])
            print prstr
        print "\n"

def holders(annotations):
    d = {}
    for lst in annotations:
        if hold_re.match(lst[3]):
            # moved from iob2():
            if lst[1].start != lst[1].stop:
                if lst[1].start in d:
                    print "{} exists.\n{}\n{}".format(lst[1], d[lst[1].start], lst)
                else:
                    d[lst[1].start] = lst
            # TODO
            #else:
            #    print lst[1].start, lst[1].stop
            #    print lst[1].start != lst[1].stop
            #    print "[expressions()] ignoring none-span-holder: {}".format(lst)
    return d

def getopinionholder(filename, examplerun=False):
    """
    TODO 
    """
    if not examplerun and (len(filename) < 23 or filename[:23] != 'database.mpqa.2.0/docs/'):
        return # Ikke i formatet fra listen til johansson/moscitti. sannsynligvis tom linje på slutten
    docid = filename[23:] # Kutter database.mpqa.2.0/docs/
    sents = t_mpqa.sentences_from_file(filename)
    sents = t_tokenizer.runrepponsentences(sents)
    #return tokens
    sents = t_postagger.pos_tag_sents_lst(sents, filename)
    #tokens = t_postagger.pos_tag_sents_lst(tokens)
    annotations = t_mpqa.annotation_tuples_from_file(filename)
    gatedic = gates(annotations)
    holder = holders(annotations)
    #print holder
    #return holder
    expr = expressions_all(annotations)[0] # todo
    #return holder
    #cur = None
    #cur_end = None
    return_lst = []
    """
    [
    {tokens: [
    {form, lemma, pos, att, holder: [], ese:[], dse:[] , ose: []}, ...
    ]}, ...
    ]
    """
    #print gatedic.keys()
    #print gatedic[1045]
    for sent in sents:
        token_lst = []
        current_gate = {}
        for token in sent:
            #print token.slice.start
            token_dic = {'form': token.token,
                         'lemma': token.lemma,
                         'pos': token.postag,
                         'holder': False,
                         'ese': False,
                         'ose': False,
                         'dse': False,
                         'slice': str(token.slice)}
            #if cur_end and cur_end <= int(token.slice.start): # TODO ?
            #    #print "her"
            #    cur = None
            #    cur_end = None

            for id, obj in current_gate.items():
                if id < token.slice.start:
                    current_gate.pop(id)
                #print id, obj
            if token.slice.start in gatedic:
                tmp = gatedic[token.slice.start]
                #if token.slice.start == 1045: print tmp
                for gate in tmp:
                    #if token.slice.start == 1045: print "G: ",  gate
                    if gate['ann_type'] != 'GATE_inside':
                        if gate['slice'].stop in current_gate:
                            current_gate[gate['slice'].stop].append(gate)
                        else:
                            current_gate[gate['slice'].stop] = [gate]
                #token_dic['GATE'] = tmp
                #current_gate[gatedic[token.slice.start]['line_id']] = token.slice.stop
            token_dic['GATE'] = []
            for i in current_gate.values():
                for j in i:
                    token_dic['GATE'].append(j)
            #if token.slice.start == 1045: print "Gate: ",  current_gate
            ## TODO - gate > lst
            if token.slice.stop in current_gate:
                current_gate.pop(token.slice.stop)
            if int(token.slice.start) in holder:
                token_dic['holder'] = True
            #if int(token.slice.start) in expr:
            #for gate in token_dic['GATE']:
            for gate in token_dic['GATE']:
                # TODO: Error - includes none-span-expr.
                tmp = gate['ann_type']
                #tmp = expr[int(token.slice.start)]
                if tmp == 'GATE_objective-speech-event':
                    token_dic['ose'] = True #tmp[4]
                elif tmp == 'GATE_expressive-subjectivity':
                    token_dic['ese'] = True #tmp[4]
                elif tmp == 'GATE_direct-subjective':
                    token_dic['dse'] = True #tmp[4]
                else:
                    # Other ann_type
                    pass #print "FEIL. {}".format(tmp)
            #if token.slice.start == 1045: print token_dic
            token_lst.append(token_dic)
        #return_lst.append({'tokens':token_lst})
        return_lst.append(token_lst)
            
    return return_lst
    #return expressions(annotations)
    #print expressions(annotations)
    #print tokens
    #print iob2(tokens, expressions(annotations))
    #return (tokens, expressions(annotations))
    #return iob2(tokens, expressions(annotations))


#TODO change nested-source to set
def getopinionholderpairs(lst):
    for sent in lst:
        holders = {}
        expressions = OrderedDict()
        for i, token in enumerate(sent):
            #print i, token
            #if token['form'] == 'He': print "t....", token
            for gate in token['GATE']:
                #print "G: {}".format(gate)
                if gate['ann_type'] == 'GATE_agent':
                    # TODO - exptype
                    if 'holder_candidate' in token and token['holder_candidate']:
                        #(token['pos'][:2] == 'NN' or token['pos'][:3] == 'PRP'):
                        if 'nested_source_split' in gate:
                            tmp = gate['nested_source_split']
                        #elif 'line_id' in gate:
                        #    tmp = gate['line_id']
                        for s in tmp:
                            if s in holders:
                                holders[s].add(i)
                            else:
                                holders[s] = set([i])
                #if token['slice'].start == 1045: print token, gate
                if (gate['line_id'] not in expressions and
                    (gate['ann_type'] == 'GATE_objective-speech-event' or
                    gate['ann_type'] == 'GATE_expressive-subjectivity' or
                    gate['ann_type'] == 'GATE_direct-subjective')):
                        #print "..."
                        expressions[gate['line_id']] = (i, gate)
        print expressions
        print holders
        for i, gate in expressions.values():
            #print "...", token_nr, sent[token_nr]
            if 'nested_source_split' in gate:
                print "G: {}".format(gate['nested_source_split'])
            else:
                print "FEIL: {}, {}".format(i, gate)
            
    #for exp in expressions
                
#b = getopinionholderpairs(a)

def getholdercandidates(lst):
    # Deprec.
    raise Exception
    for sent in lst:
        count = 0
        for i, token in enumerate(sent):
            if True and not (token['dse'] or token['ese'] or token['ose']):
                if ('head' in token and (token['pos'][:2] == 'NN' or token['pos'][:3] == 'PRP')):
                    #print token['form']
                    head_id = int(token['head'])
                    count += 1
                    token['np_num'] = count
                    if head_id != 0 and len(sent) >= head_id:
                        tmp_token = sent[head_id-1]
                        if not ('head' in tmp_token and (tmp_token['pos'][:2] == 'NN' or tmp_token['pos'][:3] == 'PRP')):
                            token['holder_candidate'] = True
                    else:
                        token['holder_candidate'] = True

def getopinionexp_iob2(filename):
    """
    TODO 
    """
    if len(filename) < 23 or filename[:23] != 'database.mpqa.2.0/docs/':
        return # Ikke i formatet fra listen til johansson/moscitti. sannsynligvis tom linje på slutten
    docid = filename[23:] # Kutter database.mpqa.2.0/docs/
    sents = t_mpqa.sentences_from_file(filename)
    sents = t_tokenizer.runrepponsentences(sents)
    sents = t_postagger.pos_tag_sents_lst(sents, filename)
    #tokens = t_postagger.pos_tag_sents_lst(tokens)
    annotations = t_mpqa.annotation_tuples_from_file(filename)
    #print expressions(annotations)
    #print tokens
    #print iob2(tokens, expressions(annotations))
    #return (tokens, expressions(annotations))
    #todo overlaps
    expressions, ignored_expr = expressions_all(annotations)
    return iob2(sents, expressions, ignored_expr)

def gates(annotations):
    d = {}
    #print annotations
    for lst in annotations:
        if lst[1].start in d:
            d[lst[1].start].append(annlsttodic(lst))
        else:
            d[lst[1].start] = [annlsttodic(lst)]
    #print d.keys()
    #print d[1045]
    return d

def annlsttodic(lst):
    if len(lst) < 5:
        d = {}
    else:
        d = lst[4]
    d['line_id'] = lst[0]
    d['slice'] = lst[1]
    d['data_type'] = lst[2]
    d['ann_type'] = lst[3]
    if 'nested-source' in d:
        d['nested_source_split'] = [s.strip() for s in d['nested-source'].split(',')]
    return d

def expressions(annotations):
    d = {}
    for lst in annotations:
        if expr_re.match(lst[3]):
            # moved from iob2():
            if lst[1].start != lst[1].stop:
                if lst[1].start in d:
                    print "{} exists.\n{}\n{}".format(lst[1], d[lst[1].start], lst)
                else:
                    d[lst[1].start] = lst
    return d

def expressions_all(annotations):
    """
    @return expressions-dict, ignored expressions-ordered-dict
    """
    d_last_end = 0
    d = {}
    d_ignored = {}
    for lst in annotations:
        if expr_re.match(lst[3]):
            cur_start = lst[1].start
            cur_end = lst[1].stop
            if cur_start != cur_end: # do not return 0-span-expressions
                if d_last_end <= cur_start: # no previous overlap
                    d_last_end = cur_end
                    d[cur_start] = lst
                else:
                    if cur_start in d_ignored:
                        d_ignored[cur_start].append(lst)
                    else:
                        d_ignored[cur_start] = [lst]
    return d, OrderedDict(sorted(d_ignored.items(), key=lambda t: t[0]))
                    
def iob2(sents, expressions, ignored=OrderedDict()):
    iob_str = ""
    ignored_str = ""
    cur = None
    cur_label = None
    cur_end = None
    for sent in sents:
        for token in sent:
            # iob2
            if cur_end <= int(token.slice.start):
                cur = None
                cur_label = None
                cur_end = None
            if int(token.slice.start) in expressions and cur:
                print cur
                raise
            if int(token.slice.start) in expressions:
                cur = expressions[int(token.slice.start)]
                cur_label = gate2label(cur)
                cur_end = cur[1].stop
                print cur_label
                iob_str += u'{}\tB-{}\n'.format(token2iob(token), cur_label)
            elif cur:
                iob_str += u'{}\tI-{}\n'.format(token2iob(token), cur_label)
            else:
                iob_str += u'{}\tO\n'.format(token2iob(token))
            # ignored
            ignored_line = u'{}'.format(token.token)
            for it in ignored.values():
                for gate in it:
                    #print gate #[1].start
                    if gate[1].start == int(token.slice.start):
                        ignored_line += u'\tB-' + gate2label(gate)
                    elif gate[1].stop > int(token.slice.start) and gate[1].start < int(token.slice.start):
                        ignored_line += u'\tI-' + gate2label(gate)
                    else:
                        ignored_line += u'\t_'
            ignored_str += u'\n' + ignored_line
        iob_str += u'\n'
        ignored_str += u'\n'
    return iob_str, ignored_str

def gate2label(gate):
    if gate[3] == 'GATE_objective-speech-event':
        return 'OSE'
    elif gate[3] == 'GATE_expressive-subjectivity':
        return 'ESE'
    elif gate[3] == 'GATE_direct-subjective':
        return 'DSE'
    else:
        print "FEIL. {}".format(tmp)
        raise

def gatestr2label(gatestr):
    if gatestr == 'GATE_objective-speech-event':
        return 'ose'
    elif gatestr == 'GATE_expressive-subjectivity':
        return 'ese'
    elif gatestr == 'GATE_direct-subjective':
        return 'dse'
    else:
        print "FEIL. {}".format(tmp)
        raise

    
#def iob2(tokens, expressions):
#    return_str = ""
#    return_ignored = ""
#    cur = None
#    cur_end = None
#    ignored = {}
#    ignored_end = {}
#    for sent in tokens:
#        for token in sent:
#            #print token
#            #print "{}-{}".format(token.token, token.slice.start)
#            #print expressions[1089]
#            #print int(token.slice.start) in expressions
#            if cur_end and cur_end <= int(token.slice.start): # TODO ?
#                cur = None
#                cur_end = None
#            if int(token.slice.start) in expressions and cur:
#                print "ignoring overlap: {}\n(continues {})".format(token, lasttoken)
#                # TODO Counter - overlap
#                #return_ignored += u'{}\tI-{}'.format(expressions[cur])
#                return_str += u'{}\tI-{}\n'.format(token2iob(token), cur)
#            elif int(token.slice.start) in expressions:
#                tmp = expressions[int(token.slice.start)]
#                #print "token: {} tmp: {}".format(token, tmp)
#                ## Following unessesary - test moved to expressions()
#                #if tmp[1].start == tmp[1].stop:
#                #    print tmp[1].start, tmp[1].stop
#                #    print "[iob2()] ignoring none-span-expression: {}".format(token)
#                #    return_str += u'{}\tO\n'.format(token2iob(tmp))
#                if True: #else:
#                    if tmp[3] == 'GATE_objective-speech-event':
#                        cur = 'OSE'
#                    elif tmp[3] == 'GATE_expressive-subjectivity':
#                        cur = 'ESE'
#                    elif tmp[3] == 'GATE_direct-subjective':
#                        cur = 'DSE'
#                    else:
#                        print "FEIL. {}".format(tmp)
#                    cur_end = tmp[1].stop
#                    return_str += u'{}\tB-{}\n'.format(token2iob(token), cur)
#                    lasttoken = token
#            elif cur:
#                return_str += u'{}\tI-{}\n'.format(token2iob(token), cur)
#            else:
#                return_str += u'{}\tO\n'.format(token2iob(token))
#        return_str += u'\n'
#    return return_str, return_ignored
                    

def token2iob(token):
    """
    """
    subj = t_subjlex.getsubj(token)
    if token.token == '#':
        tokenform = '\#'
    else:
        tokenform = token.token
    return u'{}\t{}\t{}\t{}'.format(tokenform, token.lemma, token.postag, subj)


lastcol_re = re.compile(r'\t[^\t]*$')
expr_re = re.compile(r'GATE_(objective-speech-event|direct-subjectiv|expressive-subjectiv)')
hold_re = re.compile(r'GATE_agent')
t_mpqa = mpqa.MPQA()
t_tokenizer = repp.Tokenize()
t_postagger = postag.Postag()
t_subjlex = subjlex.Subjlex()

def readiob2(file, cols=('form', 'lemma', 'pos', 'att', 'gold_label', 'label', 'label/score')):
    """
    Reads IOB2 file
    """
    f = open(file)
    sents = []
    tmp = []
    for line in f:
        #print line
        if line == "\n":
            sents.append(tmp)
            tmp = []
        elif len(line.split()) != len(cols) and line[0] == '#':
            # ignore if #
            #print line
            pass
        else:
            # ignore #
            #if line[0] != '#':
            #print "«{}»".format(line.split())
            tmp.append(splitiob2(line, cols))
    if tmp:
        sents.append(tmp)
    f.close()
    return sents

def splitiob2(line, cols):
    linesplit = line.split()
    if len(linesplit) != len(cols):
        raise ValueError('Wrong number of columns.')
    tmp = {}
    for i, col in enumerate(cols):
        tmp[col] = linesplit[i]
    return tmp

def writeconll2009(lst, file):
    """
    @param lst List of sentences with list of dics representing each word
    @return filename
    """
    # ID FORM LEMMA GPOS PPOS SPLIT FORM SPLIT LEMMA PPOSS HEAD DEPREL PRED ARG
    #f = open(file, 'w')
    f = io.open(file, 'w')
    for sent in lst:
        for i, token in enumerate(sent):
            #print token
            f.write(u"{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
                i+1,            # word id
                token['form'],  # word form
                token['lemma'], # gold lemma # 
                u"_",           # pred lemma
                token['pos'],   # gold pos # 
                u"_",           # pred pos
                u"_",           # gold feat
                u"_",           # pred feat
                u"_",           # gold head
                u"_",           # pred head
                u"_",           # gold label
                u"_",           # pred label
                u"_"            # arg
                ))
        f.write(u"\n")
    f.close()
    return file

def writeconll(lst, file):
    """
    @param lst List of sentences with list of dics representing each word
    """
    # ID FORM LEMMA GPOS PPOS SPLIT FORM SPLIT LEMMA PPOSS HEAD DEPREL PRED ARG
    #f = open(file, 'w')
    f = io.open(file, 'w')
    for sent in lst:
        for i, token in enumerate(sent):
            #print token
            f.write(u"{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
                i+1,
                token['form'],
                token['lemma'],
                u"_",
                token['pos'],
                token['form'],
                token['lemma'],
                token['pos'],
                u"0",
                u"_"
                ))
        f.write(u"\n")
    f.close()

#def readconlltolst_dic(lst, file):
#    """
#    @param lst List of sentences with list of dics representing each token
#    """
#    # ID FORM LEMMA GPOS PPOS SPLIT FORM SPLIT LEMMA PPOSS HEAD DEPREL PRED ARG
#    f = open(file, 'r')
#    tokens = None
#    count = 0
#    lcount = 0
#    newlst = []
#    for sent in lst:
#        count += 1
#        #print count
#        line = False
#        newsent = []
#        for i, token in enumerate(sent):
#            #check alignment
#            while not line or line == "\n":
#                lcount += 1
#                line = f.readline()
#                #print("L: {} «{}»".format(lcount, line))
#                #print("Empty line? {}\n{}".format(linesplit, token))
#            #print ".."
#            linesplit = line.split()
#            if linesplit[1] != token['form']:
#                print("Not aligned! l.{}\nconll: {}\ntoken: {}".format(lcount, linesplit,  token))
#                return lst
#            if len(linesplit) > 8:
#                token['head'] = linesplit[8]
#                #print linesplit
#                #print token
#            if len(linesplit) > 9:
#                token['deprel'] = linesplit[9]
#            if len(linesplit) > 10:
#                token['pred'] = linesplit[10]
#                token['arg'] = linesplit[11:]
#            newsent.append(token)
#            #print token
#            line = False
#        newlst.append(newsent)
#    f.close()
#    return lst

def readconll2009(filename):
    print "open {}".format(filename)
    f = io.open(filename, 'r') #, encoding='utf-8')
    tokens = None
    lcount = 0
    lst = []
    cursent = []
    for i, line in enumerate(f):
        if line == '\n':
            lst.append(cursent)
            cursent = []
        else:
            cursent.append(parseconll2009line(line))
    return lst

def readconll(filename):
    print "open {}".format(filename)
    f = io.open(filename, 'r') #, encoding='utf-8')
    tokens = None
    lcount = 0
    lst = []
    cursent = []
    for i, line in enumerate(f):
        if line == '\n':
            lst.append(cursent)
            cursent = []
        else:
            cursent.append(parseconllline(line))
    return lst

def parseconllline(line):
        #    f.write(u"{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
        #        i+1,            # word id 0
        #        token['form'],  # word form 1
        #        token['lemma'], # pred. lemma 2
        #        u"_",           # gold lemma 3
        #        token['pos'],   # pred. pos 4
        #        u"_",           # gold pos 5
        #        u"_",           # gold feat 6
        #        u"_",           # pred feat 7
        #        u"_",           # gold head 8 
        #        u"_",           # pred head 9
        #        u"_",           # gold label 10
        #        u"_",           # pred label 11
        #        u"_"            # attributes
        #        ))
    #check alignment
    token = {}
    linesplit = line.split('\t')
    try:
        if len(linesplit) < 11:
            #print("Not aligned! {}\n{}".format(linesplit, token))
            print "Not correct format", linesplit
            raise Exception
    except:
        print linesplit
        raise Exception
    token['id'] = linesplit[0]
    token['form'] = linesplit[1]
    token['lemma'] = linesplit[2]
    token['pos'] = linesplit[4] # pos from stanford postagger
    if len(linesplit) > 8:
        token['head'] = linesplit[8]
        #print linesplit
        #print token
    if len(linesplit) > 9:
        token['deprel'] = linesplit[9]
    if len(linesplit) > 10:
        token['pred'] = linesplit[10]
        token['arg'] = linesplit[11:]
    return token

def parseconll2009line(line):
        #    f.write(u"{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
        #        i+1,            # word id 0
        #        token['form'],  # word form 1
        #        token['lemma'], # pred. lemma 2
        #        u"_",           # gold lemma 3
        #        token['pos'],   # pred. pos 4
        #        u"_",           # gold pos 5
        #        u"_",           # gold feat 6
        #        u"_",           # pred feat 7
        #        u"_",           # gold head 8 
        #        u"_",           # pred head 9
        #        u"_",           # gold label 10
        #        u"_",           # pred label 11
        #        u"_"            # attributes
        #        ))
    #check alignment
    token = {}
    linesplit = line.split('\t')
    try:
        if len(linesplit) < 13:
            #print("Not aligned! {}\n{}".format(linesplit, token))
            print "Not correct format", linesplit
            raise Exception
    except:
        print linesplit
        raise Exception
    token['id'] = linesplit[0]
    token['form'] = linesplit[1]
    token['lemma'] = linesplit[2]
    token['pos'] = linesplit[4] # pos from stanford postagger
    if len(linesplit) > 8:
        token['head'] = linesplit[9]
        #print linesplit
        #print token
    if len(linesplit) > 9:
        token['deprel'] = linesplit[11]
    #if len(linesplit) > 10:
    #    token['pred'] = linesplit[10]
    #    token['arg'] = linesplit[11:]
    return token

def readconll2009tolst(lst, filename):
    """
    @param lst List of sentences with list of dics representing each word
    """
    # ID FORM LEMMA GPOS PPOS SPLIT FORM SPLIT LEMMA PPOSS HEAD DEPREL PRED ARG
    # ID FORM LEMMA PLEMMA POS PPOS FEAT PFEAT HEAD PHEAD LABEL PLABEL ARG
    #f = open(filename, 'r')
    print "open {}".format(filename)
    f = io.open(filename, 'r') #, encoding='utf-8')
    tokens = None
    count = 0
    lcount = 0
    newlst = []
    for sent in lst:
        count += 1
        if count == 10 or count == 100 or count % 1000 == 0:
            print "setning: {}".format(count)
        #print "setning:", count
        line = False
        newsent = []
        #    f.write(u"{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
        #        i+1,            # word id 0
        #        token['form'],  # word form 1
        #        token['lemma'], # pred. lemma 2
        #        u"_",           # gold lemma 3
        #        token['pos'],   # pred. pos 4
        #        u"_",           # gold pos 5
        #        u"_",           # gold feat 6
        #        u"_",           # pred feat 7
        #        u"_",           # gold head 8 
        #        u"_",           # pred head 9
        #        u"_",           # gold label 10
        #        u"_",           # pred label 11
        #        u"_"            # attributes
        #        ))
        for i, token_origin in enumerate(sent):
            token = copy.deepcopy(token_origin)
            #check alignment
            while not line or line == "\n":
                lcount += 1
                line = f.readline() #.decode('utf-8')
                #print("L: {} «{}»".format(lcount, line))
                #print("Empty line? {}\n{}".format(linesplit, token))
            #print ".."
            linesplit = line.split('\t')
            try:
                if linesplit[1] != token['form']:
                    #print("Not aligned! {}\n{}".format(linesplit, token))
                    print("Not aligned! l.{}\nconll: {}\ntoken: {}".format(lcount, linesplit,  token))
                    return newlst
            except:
                print linesplit
                raise
            if len(linesplit) > 8:
                token['head'] = linesplit[9]
                #print linesplit
                #print token
            if len(linesplit) > 9:
                token['deprel'] = linesplit[11]
            #if len(linesplit) > 10:
            #    token['pred'] = linesplit[10]
            #    token['arg'] = linesplit[11:]
            newsent.append(token)
            #print token
            line = False
        newlst.append(newsent)
    f.close()
    #print newlst[0][0]
    return newlst

def readconlltolst(lst, file):
    """
    @param lst List of sentences with list of dics representing each word
    """
    # ID FORM LEMMA GPOS PPOS SPLIT FORM SPLIT LEMMA PPOSS HEAD DEPREL PRED ARG
    #f = open(file, 'r')
    f = io.open(file, 'r') #, encoding='utf-8')
    #f = open(file, 'r')
    tokens = None
    count = 0
    lcount = 0
    newlst = []
    for sent in lst:
        count += 1
        if count % 1000 == 0:
            print "setning: {}".format(count)
        #print count
        line = False
        newsent = []
        for i, token in enumerate(sent):
            #print token
            #check alignment
            while not line or line == "\n":
                lcount += 1
                line = f.readline() #.decode('utf-8')
                #print("L: {} «{}»".format(lcount, line))
                #print("Empty line? {}\n{}".format(linesplit, token))
            #print ".."
            linesplit = line.split('\t')
            if linesplit[1] != token['form']:
                #print("Not aligned! {}\n{}".format(linesplit, token))
                print("Not aligned! l.{}\nconll: {}\ntoken: {}".format(lcount, linesplit,  token))
                return lst
            if len(linesplit) > 8:
                token['head'] = linesplit[8]
                #print linesplit
                #print token
            if len(linesplit) > 9:
                token['deprel'] = linesplit[9]
            if len(linesplit) > 10:
                token['pred'] = linesplit[10]
                token['arg'] = linesplit[11:]
            newsent.append(token)
            #print token
            line = False
        newlst.append(newsent)
    f.close()
    return lst

        
def writeiob2(lst, filename):
    fw = open(filename, 'w')
    for sent in lst:
        predicates = []
        for token in sent:
            pred = token['pred']
            if pred != '_':
                predicates.append(pred)
        for token in sent:
            pred = '_'
            argl = '_'
            for i, arg in enumerate(token['arg']):
                if arg != '_':
                    if pred != '_':
                        print("Mer enn et pred: {}\n{}".format(token['form'], token['arg']) )
                    pred = predicates[i]
                    argl = arg
            fw.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t-{}-\n".format(
                token['form'],
                token['lemma'],
                token['pos'],
                token['att'],
                token['head'],
                token['deprel'],
                token['pred'],
                pred + ':' + argl,
                token['gold_label']
                ))
        fw.write("\n")
    fw.close()

def sentwords_in_sent(sent):
    sentwords = []
    # find sentiment words indexes
    for i, token in enumerate(sent):
        if token['att'] != '-':
            sentwords.append(i+1)
    return sentwords

def deptree_from_sent(sent):
    deptree = {}
    inv_deptree = {}
    for i, token in enumerate(sent):
        if token['head'] in deptree:
            deptree[token['head']].append(i+1)
        else:
            deptree[token['head']] = [i+1]
        inv_deptree[str(i+1)] = token['head']
    return deptree, inv_deptree
    
# sentiment word proximity
def sentword_prox(sent):
    # for each token, find distance to nearest sentiment word
    sentwords = sentwords_in_sent(sent)
    for i, token in enumerate(sent):
        nearest = min(sentwords, key=lambda x:abs(x-i))
        if len(sentwords) == 0:
            token['sentword_prox'] = '-'
        elif abs(nearest - i) > 4:
            token['sentword_prox'] = '5'
        elif abs(nearest - i) > 2:
            token['sentword_prox'] = '3'
        elif abs(nearest - i) > 0:
            token['sentword_prox'] = '1'
        elif abs(nearest - i) == 0:
            token['sentword_prox'] = '0'

# sentiment word dep distance
def sentword_dep_dist(sent):
    distances = {}
    sentwords = sentwords_in_sent(sent)
    deptree, inv_deptree = deptree_from_sent(sent)
    for sentword in sentwords:
        count = 0
        distances[sentword] = count
        tmp = sentword
        while tmp != '0':
            print tmp
            tmp = inv_deptree[str(tmp)]
            distances[tmp] = count
    print distances
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
#    parser.add_argument("-i", dest="input_filename",
#                        help="Input file", metavar="FILE",
#                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument("-dev-train", "--devel-train", dest="devtrainset",
                        help="Create training file for devel. with devtrainset",
                        action='store_true')
    parser.add_argument("-dev-test", "--devel-test", dest="devtestset",
                        help="Create test file for devel. with devtestset",
                        action='store_true')
    parser.add_argument("-train", "--train", dest="trainset",
                        help="Create training file for final test with trainset",
                        action='store_true')
    parser.add_argument("-test", "--test", dest="testset",
                        help="Create test file for final test with testset",
                        action='store_true')
    parser.add_argument("-resultfile", "--resultfile", dest="resultfile",
                        help="iob2 input file is a resultfile",
                        action='store_true')
    parser.add_argument("-conll-input", dest="conllfile",
                        help="conll input file for merging with iob2 with gold labels as last (3rd with resultfile) column",
                        metavar="FILE"
                        )
    parser.add_argument("-iob2-input", dest="iob2file",
                        help="iob2 input file with gold labels as last (3rd with resultfile) column",
                        metavar="FILE"
)
    parser.add_argument("-add-srl-dep", "--add-srl-dep", dest="iob2_filename",
                        help="Reads file, writes conll-version (with suffix conll)", metavar="FILE")
    parser.add_argument("-i", "--interactive", dest="interactive",
                        help="For interactive development",
                        action='store_true')
    parser.add_argument("--pylab", dest="interactive",
                        help="For interactive development",
                        action='store_true')
    parser.add_argument("--automagic", dest="interactive",
                        help="For interactive development",
                        action='store_true')
    args = parser.parse_args()

    if args.interactive:
        print "Interactive"
        #test = createtrainingfile(DATA_PREFIX + "/out/trening.txt")
        #test = getopinionexp_iob2("database.mpqa.2.0/docs/20020510/21.50.13-28912")
        #test2 = getopinionexp_iob2("database.mpqa.2.0/docs/20020510/21.50.13-28912")
        #test = getopinionholder("database.mpqa.2.0/docs/20010630/00.48.42-17806")
        #test = getopinionexp_iob2("database.mpqa.2.0/docs/ula/HistoryGreek")
        #test2 = getopinionexp_iob2("database.mpqa.2.0/docs/ula/HistoryGreek")
        #testdoc = 'database.mpqa.2.0/docs/20020315/20.42.26-19148'
        #test = getopinionexp_iob2(testdoc)
        #test = "database.mpqa.2.0/docs/20010630/00.48.42-17806"
        #test = "database.mpqa.2.0/docs/20020304/20.42.01-25605" # ex 4a,  5a, 5b
        #test = "database.mpqa.2.0/docs/20020331/21.09.25-22686" # own example - terrorism .. hate
        # #test = "database.mpqa.2.0/docs/non_fbis/15.13.45-21190" # ex 4b:However
        # #test = "database.mpqa.2.0/docs/20011231/21.05.45-10422" # ex 4d, 5c
        # #test = "database.mpqa.2.0/docs/non_fbis/04.33.07-17094" # ex 6a
        # #test = "database.mpqa.2.0/docs/ula/114CUL057" # ex 6b
        #test = "database.mpqa.2.0/docs/20020510/21.50.13-28912" # SRI
        #test = 'database.mpqa.2.0/docs/20011007/03.17.23-6711'
        #a = getopinionholder(test)
        #b = writeconll(a, DATA_PREFIX + "/out/tmp2.conll")
        # lth = lth_srl.Lth_srl()
        #conlloutput = lth.run(DATA_PREFIX + "/out/tmp2.conll")
        #conlloutput = DATA_PREFIX + '/out/tmp2.conll'
        #c = readconlltolst(a, conlloutput)
        #d = getholdercandidates(c)
        #printopinionexpression(a)
        #'database.mpqa.2.0/docs/20020315/20.42.26-19148'
        #ex = expressions(s)
        #ex, ignored = getopinionexp_iob2(test)
        #foo = expressions(test2)
        #iobstr = token2iob(token)
        #iob = iob2(test[0], test[1])
        #cols=('form', 'lemma', 'pos', 'att', 'gold_label')
        #sentlst = createfile(testset=True, opinionexp=False, opinionholder=True)
        #sentlst = readiob2('/hom/trondth/Dropbox/devtrain.txt', cols)
        #newlst = readconlltolst(sentlst, '/hom/trondth/Dropbox/devtest.txt.conll.out')
        #testlst = newlst[:3]
        ###writeiob2(tstlst, "test.txt")
        #testlst = newlst[0:1]
        #sentword_dep_dist(testlst[0])
        #a = createfile("foo", opinionexp=False, opinionholder=True)
        #a = createfile("foo", opinionexp=False, opinionholder=True, testset=True)
        #sentlst = createfile("devtest.json", testset=True, opinionexp=False, opinionholder=True)
        #sentlst = createfile("devtest.json", testset=False, opinionexp=False, opinionholder=True)
        #newlst = readconlltolst(sentlst, '/home/tt/Dropbox/devtest.txt.conll.out')
        #cols=('form', 'lemma', 'pos', 'att', 'gold_label', 'label', 'label/score')
        ##exprsentlst = readiob2('/hom/trondth/master/out/minidevresult.txt', cols)
        #writeconll2009(exprsentlst, "minidevresult.conll")
        #trainsentlst = createfile(opinionexp=False, opinionholder=True, doclistfile="/config/doclists/minitrainset.txt")
        #trainsentlst_sb = readconll2009tolst(trainsentlst, "minidevtrain.conll.sb")
        #trainsentlst_dt = readconll2009tolst(trainsentlst, "minidevtrain.conll.dt")
        #trainsentlst_conll = readconll2009tolst(trainsentlst, "minidevtrain.conll.conll")
        ##writeconll2009(trainsentlst, "minidevtrain.conll")
        #testsentlst = createfile(opinionexp=False, opinionholder=True, doclistfile="/config/doclists/minitestset.txt")
        ##writeconll2009(testsentlst, "minidevtest.conll")
        #testsentlst_sb = readconll2009tolst(testsentlst, "minidevtest.conll.sb")
        #testsentlst_dt = readconll2009tolst(testsentlst, "minidevtest.conll.dt")
        #testsentlst_conll = readconll2009tolst(testsentlst, "minidevtest.conll.conll")

        #writeconll2009(a, "ex-thrives.conll2009")
        #writeconll(a, "ex-thrives.conll")
        pass
        
    if args.resultfile:
        cols=('form', 'lemma', 'pos', 'att', 'gold_label', 'label', 'label/score')
    else:
        cols=('form', 'lemma', 'pos', 'att', 'gold_label')
    if args.conllfile and args.iob2file:
        iob2lst = readiob2(args.iob2file, cols)
        fulllst = readconlltolst(iob2lst, args.conllfile)
        writeiob2(fulllst, args.iob2file + '-extended.txt')
    if args.iob2_filename:
        tmp = readiob2(args.iob2_filename, cols)
        writeconll(tmp, args.iob2_filename + ".conll")
    if args.conllfile and args.opinionholder:
        sentlst = createfile(testset=True, opinionexp=False, opinionholder=True)
        fulllst = readconlltolst(sentlst, args.conllfile)
        writeiob2(fulllst, args.iob2file + '-extended.txt')
    if args.devtestset:
        createfile("devtest.txt", testset=True)
    if args.devtrainset:
        createfile("devtrain.txt", testset=False)
    if args.testset:
        createfile("test.txt", testset=True, devset=False)
    if args.trainset:
        createfile("train.txt", testset=False, devset=False)
    
