##!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import itertools
import json
from collections import Counter
from opinionexpressions import *
from sklearn import svm
from sklearn.feature_extraction import DictVectorizer
import numpy as np
import scipy
from scipy.sparse import csgraph
import re
from sklearn.externals import joblib

re_ose = re.compile(r'GATE_objective-speech-event')
re_ese = re.compile(r'GATE_expressive-subjectiv')
re_dse = re.compile(r'GATE_direct-subjectiv')
re_holder = re.compile(r'GATE_agent')
EXPTYPES = ['dse', 'ese', 'ose']
DEPREPS = ['dt', 'sb', 'conll']
DEBUG = False
DEBUGNOW = True
counters = Counter()

def read_model(filename):
    """
    @param filename Input filename
    @return Scikit-learn classifier
    """
    return joblib.load(filename)

def write_model(clf, filename):
    """
    @param filename Output filename
    @param clf Classifier model
    """
    joblib.dump(clf, filename)

def cleanholdercandidates(lst):
    """
    Removes holder candidates. Modifies list of sentences.

    @param lst List of sentences with list of tokens.
    """
    for sent in lst:
        for token in sent:
            if 'holder_candidate' in token:
                del token['holder_candidate']

def cleanholders(lst):
    """
    Removes holders. Modifies list of sentences.

    @param lst List of sentences with list of tokens.
    """
    for sent in lst:
        for token in sent:
            token['holder'] = False
            if 'holders' in token:
                del token['holders']

def getexpressions_sent(sent, predict=False):
    """
    Collects lists of expressions in phrases.
    
    @param sent List of tokens in sent
    @return Dictionary with list of expression
    """
    expr = {}
    if predict:
        gatekey = 'PGATE'
    else:
        gatekey = 'GATE'
    for exptype in EXPTYPES:
        expr[exptype] = OrderedDict()
    for i, t in enumerate(sent):
        for gate in t[gatekey]:
            if gate['slice'].start != gate['slice'].stop:
                tmp = gate['ann_type']
                if re_ose.match(tmp):
                    if gate['line_id'] not in expr['ose']:
                        expr['ose'][gate['line_id']] = {gatekey: gate,
                                                   'token_id': set([i+1])}
                    else:
                        expr['ose'][gate['line_id']]['token_id'].add(i+1)
                elif re_ese.match(tmp): #tmp == 'GATE_expressive-subjectivity':
                    if gate['line_id'] not in expr['ese']:
                        expr['ese'][gate['line_id']] = {gatekey: gate,
                                                   'token_id': set([i+1])}
                    else:
                        expr['ese'][gate['line_id']]['token_id'].add(i+1)
                elif re_dse.match(tmp): #tmp == 'GATE_direct-subjective':
                    if gate['line_id'] not in expr['dse']:
                        expr['dse'][gate['line_id']] = {gatekey: gate,
                                                   'token_id': set([i+1])}
                    else:
                        expr['dse'][gate['line_id']]['token_id'].add(i+1)
    return expr

def tagholdercandidates_sent(sent, predict=False): 
    """
    Tags holder candidates for the different types of expressions.
    Head of noun phrases are selected as holder candidates for an
    expression type when they are not a part of an expression of that
    type.
    
    @param sent List of tokens in sent
    @param duplicates Ignore holder candidates from subtree of a holder
    """
    head_num = False
    for i, token in enumerate(sent):
        if 'daughters' not in token:
            raise ValueError("Need to run daughterlists_sent first.")
        token['holder_candidate'] = set()
        if ('head' in token and token['head'] == '0'):
            head_num = i
        if ('head' in token and (token['pos'][:2] == 'NN' or token['pos'][:3] == 'PRP')):
            head_id = int(token['head'])
            if head_id != 0 and len(sent) >= head_id:
                tmp_token = sent[head_id-1]
                if not ('head' in tmp_token and
                        (tmp_token['pos'][:2] == 'NN' or tmp_token['pos'][:3] == 'PRP')):
                    if args.restrict == 'all':
                        add_this = True
                    for exptype in EXPTYPES:
                        if args.restrict == 'sameexp': 
                            # Restrict holder candidates when building features instead
                            token['holder_candidate'].add(exptype)
                        else:
                            if predict:
                                tmpexp = 'P' + exptype
                            else:
                                tmpexp = exptype
                            try:
                                if not sent[i][tmpexp]:
                                    if not args.restrict == 'all':
                                        token['holder_candidate'].add(exptype)
                                else:
                                    add_this = False
                            except:
                                print sent
                                raise
                    if args.restrict == 'all' and add_this:
                        for exptype in EXPTYPES:
                            token['holder_candidate'].add(exptype)

            else:
                if args.restrict == 'all':
                    add_this = True
                for exptype in EXPTYPES:
                    #if i+1 not in rsets[exptype]:
                    if args.restrict == 'sameexp':
                        token['holder_candidate'].add(exptype)
                    else:
                        if predict:
                            tmpexp = 'P' + exptype
                        else:
                            tmpexp = exptype
                        if not sent[i][tmpexp]:
                            if args.restrict != 'all':
                                token['holder_candidate'].add(exptype)
                        else:
                            add_this = False
                if args.restrict == 'all':
                    if add_this:
                        token['holder_candidate'].add(exptype)
    if args.notoverlappingcandidates:
        _tagholdercandidates_sent_follow_daughters(sent, head_num)

def _tagholdercandidates_sent_follow_daughters(sent, num):
    # If HC, clean subtree
    if len(sent[num]['holder_candidate']) > 0:
        for d in sent[num]['daughters']:
            _tagholdercandidates_sent_clean_subtree(sent, int(d)-1)
    else:
        for d in sent[num]['daughters']:
            _tagholdercandidates_sent_follow_daughters(sent, int(d)-1)

def _tagholdercandidates_sent_clean_subtree(sent, num):
    sent[num]['holder_candidate'] = set()
    for n in sent[num]['daughters']:
        _tagholdercandidates_sent_clean_subtree(sent, int(n)-1)

def getholder_exp_pairs_sent(sent, expr, holders, exptype=False, isolate_exp=True, test=False):
    """
    Create a list of holder-expression-pairs.
    For writer - 
    For implicit - 
    
    @param sent List of tokens
    @param expr Dict with lists of expressions of the different types
    @param holders List of opinion holders in the sentence
    @return list of tuples (exp, holder, exptype, coref(or false, when there are no internal holders))
    """
    tuples = []
    if not exptype:
        exptypelist = EXPTYPES
    else:
        exptypelist = [exptype]
    for exptype in exptypelist:
        #print exptype
        for gate in expr[exptype].values():
            tmp = False
            try:
                tmp = gate['GATE']['nested_source_split'][-1]
            except:
                # Some expressions lack nested-source
                if DEBUG:
                    print 'missing nested-source for', gate['GATE']
                tmp = False
                counters['exp-pair no nested source'] += 1
            if tmp: 
                if tmp in holders:
                    if isinstance(holders[tmp], OrderedDict):
                        coref = []
                        for h in holders[tmp].values():
                            coref.append(h['token_id'])
                        for h in holders[tmp].values():
                            tuples.append((gate['token_id'], h['token_id'], exptype, coref))
                    else:
                        tuples.append((gate['token_id'], holders[tmp]['token_id'], exptype, False))
                elif tmp == 'writer' or tmp == 'w':
                    #print "w"
                    tuples.append((gate['token_id'], 'w', exptype, False))
                else: #Implicit
                    #print "i"
                    tuples.append((gate['token_id'], 'implicit', exptype, False))
    return tuples

def getholders_sent(sent):
    """
    @param sent List of tokens in sentence
    @return List of opinion holders in sent
    """
    raise
    holders = OrderedDict()
    for i, token in enumerate(sent):
        for gate in token['GATE']:
            if re_holder.match(gate['ann_type']):
                #print gate
                ignore_holder = False
                if 'nested_source_split' not in gate:
                    # Some GATE_agent have not id or nested-source
                    if 'id' not in gate:
                        ignore_holder = True
                    else:
                        tmp_id = gate['id']
                else:
                    tmp_id = gate['nested_source_split'][-1]
                if ignore_holder:
                    pass
                    counters['mpqa_expression_without_holder'] += 1
                elif tmp_id not in holders:
                    holders[tmp_id] = {'GATE': gate,
                        'token_id': set([i+1])}
                else:
                    holders[tmp_id]['token_id'].add(i+1)
    return holders

def getholders_sent_new(sent):
    """
    @param sent List of tokens in sentence
    @return List of opinion holders in sent
    """
    holders = OrderedDict()
    for i, token in enumerate(sent):
        for gate in token['GATE']:
            if re_holder.match(gate['ann_type']):
                #print gate
                ignore_holder = False
                if 'nested_source_split' not in gate:
                    # Some GATE_agent have not id or nested-source
                    if 'id' not in gate:
                        ignore_holder = True
                    else:
                        tmp_id = gate['id']
                else:
                    tmp_id = gate['nested_source_split'][-1]
                if ignore_holder:
                    pass
                elif tmp_id not in holders:
                    holders[tmp_id] = OrderedDict()
                    holders[tmp_id][gate['line_id']] = {'GATE': gate,
                        'token_id': set([i+1])}
                else:
                    if gate['line_id'] in holders[tmp_id]:
                        holders[tmp_id][gate['line_id']]['token_id'].add(i+1)
                    else:
                        holders[tmp_id][gate['line_id']] = {'GATE': gate,
                                                                'token_id': set([i+1])}
    return holders

def daughterlists_sent(sent):
    """
    Adds set of daughters for each token in sent.

    @param sent List of tokens in sent
    """
    for i, token in enumerate(sent):
        if 'daughters' not in token:
            token['daughters'] = set()
        head = int(token['head'])
        if 0 < head <= len(sent):
            if 'daughters' in sent[head-1]:
                sent[head-1]['daughters'].add(i+1)
            else:
                sent[head-1]['daughters'] = set([i+1])
        elif head == 0:
            pass
            #print 'root'
        else:
            print u"ERROR in conll-file. head: {}, form: {} len(sent): {}".format(head, token['form'], len(sent))
            print "Set head to 0"
            token['head'] = 0
            #raise ValueError(u"ERROR: {} {}. len(sent): {}".format(head, token['form'], len(sent)))
            
def cleandaughterlists(lst):
    """
    Removes set of daughters for each token in each sent in list.
    
    @param lst List of sentences with tokens
    """
    for sent in lst:
        for token in sent:
            if 'daughters' in token:
                del token['daughters']

def cleanpaths(sent):
    for t in sent:
        if 'paths' in t:
            del t['paths']

def getgraph_sent(sent):
    # http://docs.scipy.org/doc/scipy/reference/sparse.csgraph.html
    tmp = []
    for i, t in enumerate(sent):
        arr = [0]*len(sent)
        for num in t['daughters']:
            arr[num-1] = 1
        if t['head'] != '0':
            arr[int(t['head'])-1] = 1
        tmp.append(arr)
    graph = np.ma.masked_values(tmp, 0)
    return csgraph.csgraph_from_dense(graph)

def getpaths_sent(graph):
    return csgraph.shortest_path(graph, return_predecessors=True)
                                              
def print_path(paths, i1, i2):
    i = i1
    while i != i2:
        print(i)
        i = paths[1][i2, i]
    
def syntactic_path(cand, expr, sent, paths=False):
    """
    @param cand Token number for holder candidate (starting on 1)
    @param expr Token number for expression head (starting on 1)
    @param sent List of tokens in sentence
    @return unicode string
    """
    agg_path = u''
    if not paths:
        dist, predec = getpaths_sent(getgraph_sent(sent))
    else:
        dist, predec = paths
    # ↑ 
    # ↓
    i = i1 = cand - 1
    i2 = expr -1
    while i != i2:
        if predec[i2, i]+1 == int(sent[i]['head']):
            agg_path += sent[i]['deprel'] #unicode(i)
            agg_path += u"↑"
        elif predec[i2, i]+1 in sent[i]['daughters']:
            agg_path += sent[predec[i2, i]]['deprel'] #unicode(i)
            agg_path += u"↓"
        else:
            return "none"
            print "FEIL - ingen path funnet"
        i = predec[i2, i]
    return agg_path

def get_predicates(sent):
    preds = {}
    count = 0
    for t in sent:
        if t['pred'][0] != '_':
            preds[t['pred']] = count
            count += 1
    return preds

def shallow_sem_relation(cand, expr, sent):
    preds = get_predicates(sent)
    if sent[cand]['pred'] in preds:
        pred_i = preds[sent[cand]['pred']]-1
        tmp = sent[expr]['arg'][pred_i]
        if tmp != '_':
            return sent[expr]['arg'][pred_i]
    elif sent[expr]['pred'] in preds:
        pred_i = preds[sent[expr]['pred']]-1
        tmp = sent[cand]['arg'][pred_i]
        if tmp != '_':
            return sent[cand]['arg'][pred_i]
    else:
        return False

def token_is_holder(num, sent, pairs, exptype):
    pair_num = set()
    for p in pairs:
        if isinstance(p[1], set):
            if num in p[1]:
                pair_num.add(num)
            else:
                pass
        else:
            pass
    if pair_num:
        return (True, pair_num)
    else:
        return (False, pair_num)

def getholdercandidates_list_sent(sent):
    hc = {}
    for i, t in enumerate(sent):
        if t['holder_candidate']:
            for expt in t['holder_candidate']:
                if expt not in hc:
                    hc[expt] = set([i+1])
                else:
                    hc[expt].add(i+1)
    return hc

def getex_head(ex_set, sent):
    # return first that has head outside phrase
    for num in ex_set:
        #print ": ", sent[num-1]['head']
        try:
            if sent[num-1]['head'] not in ex_set:
                return num
        except:
            print sent
            print ex_set
            print num
            raise
            

def dom_ex_type(sent, head, transitive=False):
    """
    Return a string representing the expression type(s) of head, if exists.

    @param sent List of tokens in sentence.
    @param head Token num for expression head
    @return string
    """
    dom_ex_type_str = ''
    if not isinstance(head, int):
        head = int(head)
    if head == 0:
        return False
    if sent[head-1]['dse']:
        dom_ex_type_str += 'dse'
    if sent[head-1]['ese']:
        dom_ex_type_str += 'ese'
    if sent[head-1]['ose']:
        dom_ex_type_str += 'ose'
    if transitive and not dom_ex_type_str:
        return dom_ex_type(sent, sent[head-1]['head'])
    return dom_ex_type_str

def ex_verb_voice(sent, ex_set, be_outside_ex=True):
    """
    Finds verb voice feature.
    1. One of the tokens in the set must be partisip - VBG
    2. One of the tokens in the set must be lemma 'be'
    3. VBN's head has lemma 'be'
    
    If none of the tokens is verb, returns string 'None'

    @param sent List of tokens in sentence.
    @param ex_set set of nums in expression
    @return string Active, Passive or None
    """
    criteria_1 = False
    criteria_2 = False
    criteria_3 = False
    verb_exists = False
    _slice = []
    for num in ex_set:
        _slice.append(num-1)
        if sent[num-1]['pos'] == 'VBN':
            criteria_1 = True
            if sent[int(sent[num-1]['head'])-1]['lemma'] == 'be':
                criteria_3 = True
        if sent[num-1]['lemma'] == 'be':
            criteria_2 = True
        if sent[num-1]['pos'][0] == 'V':
            verb_exists = True
    if criteria_1 and criteria_2 and criteria_3:
        return 'Passive'
    elif criteria_1 and criteria_3 and be_outside_ex:
        _slice.sort()
        return 'Passive'
    elif verb_exists:
        return 'Active'
    else:
        return 'None'

def extolst(dict, gatekey='GATE'):
    return_lst = []
    for lst in dict.values():
        for t in lst.values():
            return_lst.append({'token_id': t['token_id'], 'expt': gatestr2label(t[gatekey]['ann_type'])})
    return return_lst

def count_sys(lst, save=False):
    return_lst = []
    exp_seen = set()
    exp_seen_set = set()
    for item in lst:
        if str(item[0]) not in exp_seen:
            exp_seen.add(str(item[0]))
            return_lst.append(item)
            #if args.onlyinternals:
            #    if not isinstance(item[1], basestring):
            #        counters['sys_len_new' + item[2]] += 1
            #else:
            counters['sys_len_new' + item[2]] += 1
    return return_lst

def count_gold(lst):
    exp_seen = set()
    exp_seen_set = set()
    for item in lst:
        if str(item[0]) not in exp_seen:
            exp_seen.add(str(item[0]))
            #if args.onlyinternals:
            #    if not isinstance(item[1], basestring):
            #        counters['gold_len_new' + item[2]] += 1
            #else:
            counters['gold_len_new' + item[2]] += 1
    for item in lst:
        if not item[0].intersection(exp_seen_set):
            exp_seen_set = exp_seen_set | item[0]
            counters['gold_len_ignoring_overlap' + item[2]] += 1

def getfeaturesandlabels(lst, exptype=False, semantic=True, predict=True):
    """
    To use with evaluation. For each expression, it will return both the corresponding gold and predicted holder.
    TODO - a version of this function without returning gold holders
    """
    if 'PGATE' in lst[0][0]:
        print "Get features from {} expressions.".format('predicted' if predict else 'gold')
    else:
        print "Get features from gold expressions. (No PGATE in token)"
        predict = False
        
    stats = {'holders_not_in_candidates': [],
             'position': {},
             'expt_not_in_candidates': []}
    if not exptype:
        exptypelist = EXPTYPES
    features = {}
    labels = {}
    pos = {}
    ev = evaluate()
    for expt in EXPTYPES:
        features[expt] = []
        labels[expt] = []
        pos[expt] = []
        features[expt+'implicit'] = []
        labels[expt+'implicit'] = []
        pos[expt+'implicit'] = []
        features[expt+'w'] = []
        labels[expt+'w'] = []
        pos[expt+'w'] = []
    for sent_i, sent in enumerate(lst):
        if DEBUG: print "---", sent_i
        if sent_i % 1000 == 0: print "setning", sent_i
        daughterlists_sent(sent)
        ex = getexpressions_sent(sent)
        pex = getexpressions_sent(sent, predict=predict)
        tagholdercandidates_sent(sent, predict=predict)
        candidates = getholdercandidates_list_sent(sent)
        holder_dct = getholders_sent_new(sent)
        holder_exp_pairs = getholder_exp_pairs_sent(sent, ex, holder_dct, test=predict)
        count_gold(holder_exp_pairs) 
        if True: # syntactic_path
            paths = getpaths_sent(getgraph_sent(sent))
        else:
            paths = False
        if predict:

            holder_exp_pairs_sys = []

            for c, p in enumerate(extolst(pex, gatekey='PGATE')):
                # first located e' that corresponded to e
                argmaxcxe = 0 # at least some overlap
                if args.argmaxcxe:
                    argmaxcxe = int(args.argmaxcxe)
                current_pair = None
                for exp_pair_i, exp_pair in enumerate(holder_exp_pairs):
                    #argmax c(x,e) regardless of exp type j&m 7.1.1
                    if DEBUG:
                        print exp_pair
                    cxe = ev.spancoverage(exp_pair[0], p['token_id']) 
                    if DEBUG:
                        print cxe
                    if cxe > argmaxcxe:
                        argmaxcxe = cxe
                        current_pair = exp_pair
                if current_pair:
                    holder_exp_pairs_sys.append((p['token_id'], current_pair[1], current_pair[2], current_pair[3]))
                else:
                    counters['falsely_detected_exp'] += 1
                    counters['falsely_detected_exp' + p['expt']] += 1
                    
        if predict:
            holder_exp_pairs_use = holder_exp_pairs_sys
        else:
            holder_exp_pairs_use = holder_exp_pairs
        holder_exp_pairs_use = count_sys(holder_exp_pairs_use, save=True)
        for exp_pair in holder_exp_pairs_use:
            expt = exp_pair[2]
            cand_exists = True
            holder_set = True
            # Categorise 
            if isinstance(exp_pair[1], str):
                #if predict:
                holder_set = False
            elif isinstance(exp_pair[1], set):
                # om holder ikke er hc
                #print candidates
                if expt in candidates:
                    if not exp_pair[1].intersection(candidates[expt]):
                        counters['holder_not_in_candidate_head'] += 1
                        cand_exists = False
                        for cand in candidates[expt]:
                            if exp_pair[1].intersection(get_subtree(sent, cand, transitive=True)):
                                cand_exists = True
                        if not cand_exists:
                            counters['holder_not_in_candidates'] += 1
                            counters['holder_not_in_candidates' + exp_pair[2]] += 1
                            stats['holders_not_in_candidates'].append({'candidates': candidates[expt],
                                                                       'exp_pair': exp_pair})
                else:
                    cand_exists = False
                    counters['ignore_count'] += 1
                    counters['holder not in candidates - special case'] += 1
            #if cand_exists:
            # For prediction:
            elif isinstance(exp_pair[1], OrderedDict):
                if expt in candidates:
                    holdermax = argmaxcxh(exp_pair[1], candidates[expt])
                    if not holdermax[0]:
                        cand_exists = False
                        counters['ignore_count'] += 1
                else:
                    cand_exists = False
                    counters['expt_not_in_candidates - new'] += 1
                    stats['expt_not_in_candidates'].append({'sent': sent_i,
                                                               'exp_pair': exp_pair})
            else:
                raise Exception('exp_pair[1] of unknown type: {}'.format(exp_pair[1]))

            if not predict or cand_exists:
                # we don't need to count false predicted holders, the p. sum is already
                # made, but we need these for training
                
                # ext-classifiers (w/imp)
                # labels
                if exp_pair[1] == 'w':
                    labels[expt + 'w'].append(True)
                    labels[expt + 'implicit'].append(False)
                elif exp_pair[1] == 'implicit':
                    labels[expt + 'w'].append(False)
                    labels[expt + 'implicit'].append(True)
                else:
                    labels[expt + 'w'].append(False)
                    labels[expt + 'implicit'].append(False)

                # Features
                featuresdict = {}
                ex_head = getex_head(exp_pair[0], sent)
                featuresdict['ex_head_word'] = sent[ex_head-1]['form']
                featuresdict['ex_head_pos'] = sent[ex_head-1]['pos']
                featuresdict['ex_head_lemma'] = sent[ex_head-1]['lemma']
                tmp = dom_ex_type(sent, sent[ex_head-1]['head'], transitive=False)
                if tmp:
                    featuresdict['dom_ex_type'] = tmp
                featuresdict['ex_verb_voice'] = ex_verb_voice(sent, exp_pair[0])
                featuresdict['deprel_to_parent'] = sent[ex_head-1]['deprel']
                features[expt + 'w'].append(featuresdict)
                #features[expt + 'implicit'].append(featuresdict)
                pos[expt + 'w'].append({'sent': sent_i,
                                             'exp': exp_pair[0],
                                                 'holder_gold': exp_pair[1],
                                           'holder_sys': 'w'})
                pos[expt + 'implicit'].append({'sent': sent_i,
                                             'exp': exp_pair[0],
                                                 'holder_gold': exp_pair[1],
                                           'holder_sys': 'implicit'})

            if cand_exists:
                # internals
                if expt in candidates:
                    featuresandlabeladded = False
                    for cand in candidates[expt]:
                        if args.restrict == 'sameexp' and cand in exp_pair[0]: #get_subtree(sent, cand, transitive=True)):
                            pass
                        else:
                            featuresdict = {}
                            if holder_set:
                                featuresandlabeladded = True

                                # labels
                                if isinstance(exp_pair[1], OrderedDict):
                                    label = cand_in_ghodct(cand, exp_pair[1])
                                if isinstance(exp_pair[1], set):
                                    label = cand in exp_pair[1]
                                elif isinstance(exp_pair[1], str):
                                    label = cand == exp_pair[1]
                                labels[expt].append(label)

                                # positions
                                pos[expt].append({'sent': sent_i,
                                                        'exp': exp_pair[0],
                                                        'holder_sys': get_subtree(sent, cand, transitive=True),
                                                        'holder_gold': exp_pair[1],
                                                        'coref_gold': exp_pair[3],
                                                        'exptype' : expt
                                                        }) 

                                # features
                                ex_head = getex_head(exp_pair[0], sent)
                                featuresdict['synt_path'] = syntactic_path(cand, ex_head,
                                                                           sent, paths=paths)
                                if semantic:
                                    tmp = shallow_sem_relation(cand-1, ex_head-1, sent)
                                    if tmp:
                                        featuresdict['shal_sem_rel'] = tmp
                                featuresdict['ex_head_word'] = sent[ex_head-1]['form']
                                featuresdict['ex_head_pos'] = sent[ex_head-1]['pos']
                                featuresdict['ex_head_lemma'] = sent[ex_head-1]['lemma']
                                featuresdict['cand_head_word'] = sent[cand-1]['form']
                                featuresdict['cand_head_pos'] = sent[cand-1]['pos']
                                tmp = dom_ex_type(sent, sent[ex_head-1]['head'], transitive=False)
                                if tmp:
                                    featuresdict['dom_ex_type'] = tmp
                                featuresdict['ex_verb_voice'] = ex_verb_voice(sent, exp_pair[0])
                                if cand > 1:
                                    featuresdict['context_r_word'] = sent[cand-2]['form']
                                    featuresdict['context_r_pos'] = sent[cand-2]['pos']
                                if cand < len(sent):
                                    featuresdict['context_l_word'] = sent[cand]['form']
                                    featuresdict['context_l_pos'] = sent[cand]['pos']
                                featuresdict['deprel_to_parent'] = sent[ex_head-1]['deprel']
                                    
                                features[expt].append(featuresdict)
                else:
                    counters["expt_not_in_candidates"] += 1
                    counters["expt_not_in_candidates" + expt] += 1

    stats['positions'] = pos
    return features, labels, stats

def argmaxcxh(ghodct, ph):
    curmax = 0
    cur = False
    for h in ghodct.values():
        cxh = spancoverage(ph, h['token_id'])
        if cxh > curmax:
            curmax = cxh
            cur = h
    return cur, curmax

def cand_in_ghodct(cand, ghodct):
    for h in ghodct.values():
        if cand in h['token_id']:
            return True
    return False
    
        
def create_matrix(features, labels):
    """
    @return vec, X, y
    """
    vec = DictVectorizer()
    X = vec.fit_transform(features)
    y = np.array(labels)
    return vec, X, y

def transform_to_matrix(features, labels, vec):
    """
    @return X, y
    """
    X = vec.transform(features)
    y = np.array(labels)
    return X, y
    

def create_model(X, y):
    try:
        clf = svm.SVC(probability=True, kernel='linear')
        clf.fit(X, y)
        return clf
    except:
        return False

def token_exp(token, exptype=False):
    """
    @return set of exp-line_ids from GATE
    """
    line_ids = set()
    for gate in token['GATE']:
        if ((not exptype or exptype == 'ese') and re_ese.match(gate['ann_type'])):
            line_ids.add(gate['line_id'])
        if ((not exptype or exptype == 'ose') and re_ose.match(gate['ann_type'])):
            line_ids.add(gate['line_id'])
        if ((not exptype or exptype == 'dse') and re_dse.match(gate['ann_type'])):
            line_ids.add(gate['line_id'])
    return line_ids

def count_holder_candidates(lst, exptype=False, check_exp=False):
    # TODO Check for individual exptypes
    counters = {
        'sents': 0,
        'has_holder_candidate': 0,
        'holders_are_not_candidates': 0,
        'holders': 0,
        'count_exp': 0
        }
    for sent in lst:
        holder_candidates = 0
        holders_are_not_candidates = False
        exps = set()
        for t in sent:
            t_exp = token_exp(t, exptype)
            exps |= t_exp
            if 'holder_candidate' in t:
                pass
    return counters

def cleanupnonespanexpressions(lst, partial=True):
    for sent in lst:
        for t in sent:
            t['dse'] = False
            t['ese'] = False
            t['ose'] = False
            for gate in t['GATE']:
                if partial:
                    if gate['slice'].start != gate['slice'].stop:
                        tmp = gate['ann_type']
                        #if tmp == 'GATE_objective-speech-event':
                        if re_ose.match(tmp):
                            t['ose'] = True #tmp[4]
                        elif re_ese.match(tmp): #tmp == 'GATE_expressive-subjectivity':
                            t['ese'] = True #tmp[4]
                        elif re_dse.match(tmp): #tmp == 'GATE_direct-subjective':
                            t['dse'] = True #tmp[4]
                else:
                    str = t['slice'][6:-1].split(',')
                    tslice = slice(int(str[0]), int(str[1]))
                    if (gate['slice'].start != gate['slice'].stop and
                            gate['slice'].stop >= tslice.stop):
                        tmp = gate['ann_type']
                        #if tmp == 'GATE_objective-speech-event':
                        if re_ose.match(tmp):
                            t['ose'] = True #tmp[4]
                        elif re_ese.match(tmp): #tmp == 'GATE_expressive-subjectivity':
                            t['ese'] = True #tmp[4]
                        elif re_dse.match(tmp): #tmp == 'GATE_direct-subjective':
                            t['dse'] = True #tmp[4]
            
def count_holder_candidates_missing(lst, holder_exp_pairs):
    holder_candidates = 0
    holder_candidates_in_other_expression = 0
    holder_candidates_in_other_expression_that_is_holder = 0
    not_holder_candidates_that_is_holder = 0
    sentences_without_holder_candidate = 0
    sentences_without_holder_candidate_all = 0
    sentences = 0
    for i, sent in enumerate(lst):
        sentences += 1
        has_hc_all = False
        has_hc = False
        for t in sent:
            if len(t['holder_candidate']) > 0:
                holder_candidates += 1
                has_hc_all = True
                if len(t['holder_candidate']) < 3:
                    holder_candidates_in_other_expression += 1
                else:
                    has_hc = True
        if not has_hc:
            sentences_without_holder_candidate += 1
    print "HC: ", holder_candidates
    print "HC, in expression of another type: ", holder_candidates_in_other_expression
    print "Sents: ", sentences
    print "Sents without HC: ", sentences_without_holder_candidate
    print "Sents without HC (restriction on same expression type): ", sentences_without_holder_candidate_all
    
def count_span_shorter_than_token(lst):
    sents = 0
    tokens = 0
    tokens_not_0 = 0
    spans = 0
    sent_n = 0
    for sent in lst:
        count_sent = False
        token_n_hit = []
        token_n = 0
        for token in sent:
            count_token = False
            token_len = token['slice'].stop - token['slice'].start
            for gate in token['GATE']:
                gate_len = gate['slice'].stop - gate['slice'].start
                if gate_len < token_len and gate_len != 0:
                    spans += 1
                    count_token = True
                    count_sent = True
            if count_token:
                tokens += 1
                token_n_hit.append(token_n)
                if token_n != 0:
                    tokens_not_0 += 1
            token_n += 1 
        if count_sent:
            print sent_n, token_n_hit
            sents += 1
        sent_n += 1
    return {'sents': sents, 'tokens': tokens, 'spans': spans, 'tokens_not_0': tokens_not_0}
            
def get_subtree(sent, num, transitive=True):
    # Gets the whole subtree, this is a problem with holders like michael hirsch ..., sent 1271 devtestset
    span = set([num])
    daughters = sent[num-1]['daughters']
    if transitive:
        for d in daughters:
            span = span.union(get_subtree(sent, d, transitive=transitive))
    else:
        span = span.union(daughters)
    return span

def find_ex_sent(lst):
    for i, s in enumerate(lst):
        crit1 = False
        crit2 = False
        crit3 = False
        if len(s) < 10:
            for t in s:
                if t['ese'] or t['dse']: crit1 = True
                if t['form'].lower() == 'the': crit2 = True
                for g in t['GATE']:
                    if g['ann_type'] == 'GATE_agent':
                        crit3 = True
        if crit1 and crit2 and crit3: print i

class evaluate:

    def __init__(self, labels=EXPTYPES):
        self.labels = []
        for label in labels:
            self.labels.extend([label, label + 'w', label + 'implicit'])
        self.sums = {}
        self.counts = {}
        for label in self.labels:
            self.sums[label] = {'p': 0, 'r': 0}
            self.counts[label] = {'p': 0, 'r': 0}
        self.current_ex = None

    def spancoverage(self, span, spanprime):
        if isinstance(span, basestring) or isinstance(spanprime, basestring):
            if span == spanprime:
                return 1
            else:
                return 0
        tmp = span.intersection(spanprime)
        if tmp:
            return float(len(tmp)) / len(spanprime)
        return 0
    
    def spansetcoverage(self, spanset, spansetprime):
        sum = 0.0
        for spanprime in spansetprime:
            for span in spanset:
                sum += self.spancoverage(span, spanprime)
        return sum

    def get_unique_exp(self, s_p_g, exptype, count=True):
        unique_exp_s_p = []
        # cur = False
        # for item in s_p_g:
        #     if cur and (cur['sent'] == item['sent'] and
        #         cur['exp'] == item['exp']):
        #         pass
        #     else:
        #         unique_exp_s_p.append(item)
        #     cur = item

        exp_seen = set()
        exp_seen_set = set()
        for item in s_p_g:
            if ('i' + str(item['exp']) + 's' + str(item['sent'])) not in exp_seen:
                exp_seen.add('i' + str(item['exp']) + 's' + str(item['sent']))
                counters['gold_len_new_getunique' + exptype] += 1
                unique_exp_s_p.append(item)

        #if args.onlyinternals:
        #    for item in unique_exp_s_p:
        #        if item['holder_gold'] == 'w':
        #            counter['g_holder_w_' + item['exp']] += 1
        #            if self.spancoverage(item['holder_gold'], item['holder_sys']) > 0:
        #                counter['s_holder_w_' + item['exp']] += 1
        #        if item['holder_gold'] == 'implicit':
        #            counter['g_holder_implicit_' + item['exp']] += 1
        #            if self.spancoverage(item['holder_gold'], item['holder_sys']) > 0:
        #                counter['g_holder_implicit_' + item['exp']] += 1
        return unique_exp_s_p

    def merge_system_pairs(self, s_p_int, s_p_imp=False, s_p_w=False):
        """
        @param s_p_gold list of gold exp-holder pairs
        @return List of system pairs for unique expressions with highest confidence score
        """
        try:
            if s_p_int:
                counters['s_p_int'] = len(s_p_int)
            if not s_p_imp and not s_p_w:
                return s_p_int
        except:
            print "1029-feil"
            print s_p_int
            print s_p_imp
            print s_p_w
        s_p = []
        if not s_p_imp:
            s_p_imp = []
        if not s_p_w:
            s_p_w = []
        if DEBUG:
            for it in s_p_int:
                print it['sent'], it['exp'], it['holder_gold']
            for it in s_p_w:
                print it['sent'], it['exp'], it['holder_gold']
        for cur_int, cur_imp, cur_w in itertools.izip_longest(s_p_int, s_p_imp, s_p_w):
            skipthis = False
            if cur_int:
                cur = cur_int
            elif cur_imp:
                cur = cur_imp
            elif cur_w:
                cur = cur_w
            else:
                print "THIS IS NOT A PAIR"
                skipthis = True
            if not skipthis:
                if cur_imp and (cur_imp['confidence'] > 0.5 and cur_imp['confidence'] > cur['confidence']) or cur['confidence'] == 0:
                    if cur_imp['sent'] != cur['sent']:
                        raise
                    cur = cur_imp
                if cur_w:
                    if cur_w['sent'] != cur['sent']:
                        print "int.. ", len(s_p_int)
                        print "imp.. ", len(s_p_imp)
                        print "w..   ", len(s_p_w)
                        print cur_w
                        print cur
                        raise
                    if (cur_w['confidence'] > 0.5 and cur_w['confidence'] > cur['confidence']) or cur['confidence'] == 0:
                        cur = cur_w
                s_p.append(cur)
        if DEBUG:
            print "Pairs"
            for p in s_p:
                print p
        return s_p
            

    def get_system_pairs_prob(self, lst, results, gold_lst):
        """
        Return a list of pairs detected by system and the confidence level.
        For the gold expr, we can ignore the 
        """
        system_pairs = []

        counters['getsp gold lst'] = len(gold_lst)
        
        if isinstance(results, np.ndarray):
            cur = None
            curmax = -1
            for i, item in enumerate(lst):
                if cur and (item['sent'] != cur['sent'] or
                                item['exp'] != cur['exp']):
                    cur.update({'confidence': curmax})
                    system_pairs.append(cur)
                    curmax = -1
                    cur = None
                if not cur:
                    curmax = results[i][1]
                    cur = item
                if results[i][1] > curmax:
                    curmax = results[i][1]
                    cur = item
            if cur:
                cur.update({'confidence': curmax})
                system_pairs.append(cur)

            c = 0
            s_p_new = []
            for it in gold_lst:
                if len(system_pairs) > c:
                    if (it['sent'] == system_pairs[c]['sent'] and
                       it['exp'] == system_pairs[c]['exp']):
                        s_p_new.append(system_pairs[c])
                        c += 1
                    else:
                        it['confidence'] = 0
                        s_p_new.append(it)
                        if DEBUG: print "skip", it

            system_pairs = s_p_new

            cur = False
            for item in system_pairs:
                if cur and (cur['sent'] == item['sent'] and
                    cur['exp'] == item['exp']):
                    print "MUL: ", cur, '\n', item
                    print "MULTIPLE EXP IN EXP_PAIRS"
                    raise
                cur = item

            return system_pairs
        

        for i, item in enumerate(lst):
            if results[i]:
                system_pairs.append(item)
        return system_pairs

    def get_system_pairs(self, lst, results, s_p_imp=False, s_p_w=False):
        """
        Return a list of pairs detected by system.
        For the gold expr, we can ignore the 
        """
        
        system_pairs = []
        if isinstance(results, np.ndarray):
            cur = None
            curmax = None
            for i, item in enumerate(lst):
                if cur and item['sent'] != cur['sent']:
                    system_pairs.append(cur)
                    cur = None
                if not cur:
                    curmax = results[i][1]
                    cur = item
                if results[i][1] > curmax:
                    curmax = results[i][1]
                    cur = item

            if cur:
                system_pairs.append(cur)
            return system_pairs

        for i, item in enumerate(lst):
            if results[i]:
                system_pairs.append(item)
        return system_pairs
        
    def spansetcoverage_o(self, lst):
        prec_sum = 0.0
        rec_sum = 0.0
        for item in lst:
            prec_sum += self.spancoverage(item['holder_sys'], item['holder_gold'])
            rec_sum += self.spancoverage(item['holder_gold'], item['holder_sys'])
        return {'p': prec_sum/len(lst), 'r': rec_sum/len(lst)}

    def check_coref(self, coref, sys):
        maxcxh = -1
        argmaxcxh = False
        for item in coref:
            tmp = self.spancoverage(item, sys)
            if tmp > maxcxh:
                maxcxh = tmp
                argmaxcxh = item
        return argmaxcxh

    def spansetcoverage_o_p(self, lst, exptype=False):
        sys_len = 0
        gold_len = 0
        prec_sum = 0.0
        rec_sum = 0.0
        for item in lst:
            if 'coref_gold' in item and len(item['coref_gold']) > 1:
                holder_gold = self.check_coref(item['coref_gold'], item['holder_sys'])
            else:
                holder_gold = item['holder_gold']
            rec_sum += self.spancoverage(item['holder_sys'], holder_gold)
            prec_sum += self.spancoverage(holder_gold, item['holder_sys'])
        if exptype:
            gold_len = counters['gold_len_new' + exptype] 
            sys_len = (counters['sys_len_new' + exptype] 
                    + counters['falsely_detected_exp' + exptype])
            if False: # args.onlyinternals:
                sys_len -= counters['expt_not_in_candidates' + exptype]
            
        else:
            for exp in EXPTYPES:
                gold_len += counters['gold_len_new' + exp] 
                sys_len += counters['sys_len_new' + exp] 
            sys_len += counters['falsely_detected_exp']
            if False: # args.onlyinternals:
                sys_len -= counters['expt_not_in_candidates']

        if DEBUGNOW:
            print "exptype: {}".format(exptype)
            print "prec_sum: {} (del p s len)".format(prec_sum)
            print "rec_sum: {} (del p g len)".format(rec_sum)
            print 'gold len: {}'.format(gold_len)
            print 'sys len: {}'.format(sys_len)
        return {'p': prec_sum/sys_len, 'r': rec_sum/gold_len}

def print_tikzdep(sent):
    for i, t in enumerate(sent):
        if t['head'] == 0 or t['head'] == '0':
            print "\deproot{" + str(i+1) + "}{ROOT}"
        else:
            print "\depedge{" + t['head'] + "}{" + str(i+1) + "}{" + t['deprel'] + '}'

def print_stats(tset, exptype=EXPTYPES, deprep=False):
    cleanupnonespanexpressions(tset)
    cleanholders(tset)
    cleanholdercandidates(tset)
    print "== deprep", deprep, "=="
    f, l, s = getfeaturesandlabels(tset, semantic=False)
    for exp in EXPTYPES:
        print exp + ":", len(f[exp])
        print exp + " w/imp:", len(f[exp + 'w'])

def print_eval(trainset, testset, exptypes=EXPTYPES, semantic=False, savemodels=False, loadmodels=False, deprep=False, externals=True, predict=True):
    """
    Runs the system, prints P/R/F to stdout.

    @param trainset list of sentences with lists of tokens
    @param testset list of sentences with lists of tokens
    """
    system_pairs = []
    print "== cleaning lsts =="
    cleanupnonespanexpressions(testset)
    cleanholdercandidates(testset)
    cleanholders(testset)
    cleanupnonespanexpressions(trainset)
    cleanholdercandidates(trainset)
    cleanholders(trainset)
    
    print "== train =="
    ev = evaluate()
    features, labels, stats = getfeaturesandlabels(trainset, semantic=semantic, predict=False)
    print counters, '\n'

    print "== test =="
    counters.clear()
    ftest, ltest, stest = getfeaturesandlabels(testset, semantic=semantic, predict=predict)
    print counters
    for exp in exptypes:
        vec, X, y = create_matrix(features[exp], labels[exp])
        if externals:
            vecw, Xw, yw = create_matrix(features[exp + 'w'], labels[exp + 'w'])
            vecimp, Ximp, yimp = create_matrix(features[exp + 'w'], labels[exp + 'implicit'])
        if loadmodels:
            clf = read_model(loadmodels + exp)
        else:
            clf = create_model(X, y)
            if externals:
                clfw = create_model(Xw, yw)
                clfimp = create_model(Ximp, yimp)
            if savemodels:
                write_model(clf, savemodels + exp)
        print "== eval =="
        if deprep:
            print "== {} ==".format(deprep)
        Xt, yt = transform_to_matrix(ftest[exp], ltest[exp], vec)
        if externals:
            Xtw, ytw = transform_to_matrix(ftest[exp + 'w'], ltest[exp + 'w'], vecw)
            Xtimp, ytimp = transform_to_matrix(ftest[exp + 'w'], ltest[exp + 'implicit'], vecimp)
        results = clf.predict_proba(Xt)
        s_p_w = False
        s_p_imp = False
        gold_p1 = ev.get_unique_exp(copy.deepcopy(stest['positions'][exp + 'w']), exp, count=False)
        gold_p2 = copy.deepcopy(gold_p1)
        gold_p3 = copy.deepcopy(gold_p1)
        if clfw:
            resultsw = clfw.predict_proba(Xtw)
            s_p_w=ev.get_system_pairs_prob(stest['positions'][exp + 'w'], resultsw, gold_p1)
            counters['s_p_w' + exp] = len(s_p_w)
            if DEBUG:
                print "RESULTSW"
                print resultsw
        if clfimp:
            resultsimp = clfimp.predict_proba(Xtimp)
            s_p_imp=ev.get_system_pairs_prob(stest['positions'][exp + 'implicit'], resultsimp, gold_p2)
            counters['s_p_imp' + exp] = len(s_p_imp)
            if DEBUG:
                print "RESULTSIMP"
                print resultsimp
        s_p_int=ev.get_system_pairs_prob(stest['positions'][exp], results, gold_p3)
        counters['s_p_int' + exp] = len(s_p_int)
        system_pairs_exp = ev.merge_system_pairs(s_p_int, s_p_imp=s_p_imp, s_p_w=s_p_w)
        counters['system_pairs_all' + exp] = len(system_pairs_exp)
        for pair in system_pairs_exp:
            if 'confidence' in pair and pair['confidence'] > 0:
                counters['system_pairs' + exp] += 1
        if predict:
            ssc_exp = ev.spansetcoverage_o_p(system_pairs_exp, exptype=exp)
            print "system exp - {}:\n{}".format(exp, prf_prettystring(ssc_exp))
        else:
            ssc_exp = ev.spansetcoverage_o_p(system_pairs_exp, exptype=exp)
            print "gold exp - {}:\n{}".format(exp, prf_prettystring(ssc_exp))
        system_pairs.extend(system_pairs_exp)
    if predict:
        ssc = ev.spansetcoverage_o_p(system_pairs)
        print "system exp - all:\n", prf_prettystring(ssc)
    else:
        ssc = ev.spansetcoverage_o_p(system_pairs)
        print "gold exp - all: \n", prf_prettystring(ssc)
    
    for k,v in sorted(counters.items(), key=lambda x: x[0]):
        print k, v
    if isinstance(deprep, basestring):
        dump_jsonfile(system_pairs, 'system_pairs-' + deprep + '.json')
    return {'stats': stest, 'system_pairs': system_pairs}

def prf_prettystring(ssc=False, p=False, r=False):
    if ssc:
        p=ssc['p']
        r=ssc['r']
    return "P: {}\nR: {}\nF: {}\n".format(p, r, fscore(p, r))

def fscore(p, r):
    if p + r == 0:
        return 0
    return 2 * p * r / (p + r)

def create_gates(lst):
    #    raise Exception
    tmp_offset_start = 0
    tmp_offset_end = 0
    exp_count = 0
    for sent in lst:
        cur_exp = False
        for token in sent:
            tmp_offset_end = tmp_offset_start + len(token['form'])
            token['slice'] = slice(tmp_offset_start, tmp_offset_end)
            if 'label' not in token:
                raise Exception
            if token['label'] == 'O' or token['label'][0] == 'B':
                if cur_exp:
                    cur_exp['PGATE'][0]['slice'] = slice(last_token['PGATE'][0]['slice_start'], last_token['slice'].stop)
                    cur_exp = False
            token['Pdse'] = False
            token['Pese'] = False
            token['Pose'] = False
            if token['label'][0] == 'B':
                exp_count += 1
                token['PGATE'] = [{'ann_type': labeltoanntype(token['label']),
                                      'data_type': 'string',
                                      'slice_start': tmp_offset_start,
                                      'line_id': exp_count}]
                token['P' + token['label'][2:]] = True
                cur_exp = token
            if token['label'][0] == 'I':
                token['PGATE'] = last_token['PGATE']
                token['P' + token['label'][2:]] = True
            if 'PGATE' not in token:
                token['PGATE'] = []
            tmp_offset_start = tmp_offset_end + 1
            last_token = token
        # cleanup
        if cur_exp:
            cur_exp['PGATE'][0]['slice'] = slice(last_token['PGATE'][0]['slice_start'], last_token['slice'].stop)
        for token in sent:
            if 'Pdse' not in token:
                print sent
                raise

def labeltoanntype(label):
    if label == "B-ESE" or label == "I-ESE":
        return 'GATE_expressive-subjectivity'
    if label == "B-OSE" or label == "I-OSE":
        return 'GATE_objective-speech-event'
    if label == "B-DSE" or label == "I-DSE":
        return 'GATE_direct-subjective'
    else:
        print "Unknown label: {}".format(label)
        raise Exception

def jointestandresult(tlst, rlst):
    newlst = []
    c = 0
    if len(tlst) != len(rlst):
        raise ValueError("Lists not equal length ({} / {})".format(len(tlst), len(rlst)))
    for tsent,rsent in itertools.izip(tlst, rlst):
        if len(tsent) != len(rsent):
            raise ValueError("Sents not equal length: {}".format(c))
        c += 1
        newsent = []
        for ttoken, rtoken in itertools.izip(tsent, rsent):
            if ttoken['form'] != rtoken['form']:
                print c
                print "sent: {}\n{}\n "
                print ttoken['form']
                print rtoken['form']
            newtoken = copy.deepcopy(ttoken)
            newtoken['PGATE'] = rtoken['PGATE']
            newtoken['Pdse'] = rtoken['Pdse']
            newtoken['Pese'] = rtoken['Pese']
            newtoken['Pose'] = rtoken['Pose']
            newtoken['label'] = rtoken['label']
            newtoken['label/score'] = rtoken['label/score']
            newsent.append(newtoken)
        newlst.append(newsent)
    return newlst

def featurestats(lst, features='all'):

    allfeatures = {'synt_path', 'ex_head_word', 'ex_head_lemma', 'ex_head_pos', 'cand_head_pos', 'cand_head_word', 'dom_ex_type', 'ex_verb_voice', 'context_r_pos',
                'context_r_word', 'context_l_pos', 'context_l_word', 'deprel_to_parent'}
    if features == 'all':
        features = allfeatures
    if isinstance(features, basestring):
        features = {features}
    examplecount = 0
    featurecounter = {}
    featurecounters = {}
    for exp in EXPTYPES:
        featurecounters[exp] = {}
    for it in allfeatures:
        featurecounter[it] = Counter()
        for exp in EXPTYPES:
            featurecounters[exp][it] = Counter()
    othercounters = Counter()
    for i, sent in enumerate(lst):
        ex = getexpressions_sent(sent)
        holder_dct = getholders_sent_new(sent)
        holder_exp_pairs = getholder_exp_pairs_sent(sent, ex, holder_dct)
        for pair in holder_exp_pairs:
            if pair[1] == 'w':
                othercounters['w'] += 1
            elif pair[1] == 'implicit':
                othercounters['implicit'] += 1
            elif isinstance(pair[1], OrderedDict):
                othercounters['OrderedDict'] += 1
            elif isinstance(pair[1], set):
                ex_head = getex_head(pair[0], sent)
                cand = getex_head(pair[1], sent)
                othercounters['internal holders'] += 1
                othercounters['internal holders' + pair[2]] += 1

                # 'synt_path'
                syntpath = syntactic_path(getex_head(pair[1], sent), ex_head, sent)
                featurecounter['synt_path'][syntpath] += 1
                featurecounters[pair[2]]['synt_path'][syntpath] += 1
                othercounters['synt_path Length (only arrows)'] += syntpath.count(u'↑') + syntpath.count(u'↓')
                othercounters['synt_path Length (only arrows)' + pair[2]] += syntpath.count(u'↑') + syntpath.count(u'↓')
                
                # 'ex_head_word'
                # 'ex_head_lemma'
                # 'ex_head_pos'
                featurecounter['ex_head_word'][sent[ex_head-1]['form']] += 1
                featurecounter['ex_head_pos'][sent[ex_head-1]['pos']] += 1
                featurecounter['ex_head_lemma'][sent[ex_head-1]['lemma']] += 1

                # 'cand_head_pos'
                ## if DEBUG and examplecount < 5:
                ##     if sent[getex_head(pair[1], sent)-1]['pos'] == 'JJ':
                ##         print '\n\n'
                ##         print sent
                ##         print '\n\n'
                ##         examplecount += 1
                ## featurecounter['cand_head_pos'][sent[getex_head(pair[1], sent)-1]['pos']] += 1
                ## featurecounters['cand_head_pos'][pair[2]][sent[getex_head(pair[1], sent)-1]['pos']] += 1
                
                # 'cand_head_word'
                featurecounter['cand_head_word'][sent[cand-1]['form']] += 1
                featurecounter['cand_head_pos'][sent[cand-1]['pos']] += 1
                
                # 'dom_ex_type'
                tmp = dom_ex_type(sent, sent[ex_head-1]['head'], transitive=False)
                if tmp:
                    featurecounter['dom_ex_type'][tmp] += 1

                # 'ex_verb_voice'
                featurecounter['ex_verb_voice'][ex_verb_voice(sent, pair[0])] += 1

                # 'context_r_pos'
                # 'context_r_word'
                # 'context_l_pos'
                # 'context_l_word'
                if cand > 1:
                    featurecounter['context_r_word'][sent[cand-2]['form']] += 1
                    featurecounter['context_r_pos'][sent[cand-2]['pos']] += 1
                if cand < len(sent):
                    featurecounter['context_l_word'][sent[cand]['form']] += 1
                    featurecounter['context_l_pos'][sent[cand]['pos']] += 1

                # 'deprel_to_parent'
                if 'deprel_to_parent' in features:
                    depreltoparent = sent[ex_head-1]['deprel']
                    featurecounter['deprel_to_parent'][depreltoparent] += 1
                    featurecounters[pair[2]]['deprel_to_parent'][depreltoparent] += 1
                                    
    if 'synt_path' in args.featurestats:
        othercounters['synt_path ' + 'Average length (only arrows)'] = (
                othercounters['synt_path ' + 'Length (only arrows)'] / othercounters['internal holders'])
        for exp in EXPTYPES:
            othercounters['synt_path ' + 'Average length (only arrows) for', exp] = (
                    othercounters['synt_path ' + 'Length (only arrows)' + exp]) / othercounters['internal holders' + exp] 
    return featurecounter, featurecounters, othercounters

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-load", "--load-json-file", dest="load json-file",
                        help="Load json-file",
                        metavar="FILE")
    parser.add_argument("-save", "--save-linear-training-file",
                        help="Save training file",
                        metavar="FILE")
    parser.add_argument("-i", "--interactive", dest="interactive",
                        help="For interactive development",
                        action='store_true')
    parser.add_argument("--pylab", dest="interactive",
                        help="For interactive development",
                        action='store_true')
    parser.add_argument("--automagic", dest="interactive",
                        help="For interactive development",
                        action='store_true')
    parser.add_argument("--semantic", dest="semantic",
                        help="use semantic features",
                        action="store_true")
    parser.add_argument("-predict", "--predict", dest="predict",
                            help="Use predicted expressions", action='store_true')
    parser.add_argument("-train", "--train-file", dest="train",
                            help="Create conll-file", action='store_true')
    parser.add_argument("-test", "--test-file", dest="test",
                            help="Create conll-file", action='store_true')
    parser.add_argument("--held-out", dest="heldout", help="Train on held-out",
                        action='store_true')
    parser.add_argument("-e", "--eval", dest="eval", help="run system and print evaluation",
                        action='store_true')
    parser.add_argument("-jtrain", dest="jtrain", metavar="FILE")
    parser.add_argument("-jtest", dest="jtest", metavar="FILE")
    parser.add_argument("-ctrain", dest="ctrain", metavar="FILE")
    parser.add_argument("-ctest", dest="ctest", metavar="FILE")
    parser.add_argument("-lthsrl", dest="lthsrl", action='store_true')
    parser.add_argument("-argmaxcxe", help='a value below 0 will include system exp without overlap to a gold exp')
    parser.add_argument("-stats", "--stats")
    parser.add_argument("-notoverlappingcandidates", dest="notoverlappingcandidates", action='store_true')
    # todo - bedre navn
    parser.add_argument("-restrict", default='sameexp', choices=['all', 'sameexp', 'sametype'])
    #parser.add_argument("-notsameexp", help="todo", action='store_true')
    #parser.add_argument("-restrict_same_exp", help="todo", action='store_true')
    #parser.add_argument("-restrict_same_type", help="todo", action='store_true')
    parser.add_argument("-iob2", dest="iob2", help="Read output data from opinion expression detection", metavar="FILE")
    parser.add_argument("-savejson", dest="savejson", metavar="FILE")
    parser.add_argument("-savemodels", dest="savemodels", metavar="FILE")
    parser.add_argument("-loadmodels", dest="loadmodels", metavar="FILE")
    parser.add_argument("-loadjsonlist", metavar="FILE")
    parser.add_argument("-featurestats", choices=[
        'all', 'synt_path', 'ex_head_word', 'ex_head_lemma', 'ex_head_pos', 'cand_head_pos', 'cand_head_word', 'dom_ex_type', 'ex_verb_voice', 'context_r_pos',
                'context_r_word', 'context_l_pos', 'context_l_word', 'deprel_to_parent'
        ])
    args = parser.parse_args()

    print "= ARGS =\n", args

    if args.loadjsonlist:
        print "= LOAD JSON ="
        lst = read_jsonfile(args.loadjsonlist)

    if args.featurestats:
        
        for dep in DEPREPS:
            if args.featurestats == 'all':
                features = ['synt_path', 'ex_head_word', 'ex_head_lemma', 'ex_head_pos', 'cand_head_pos', 'cand_head_word', 'dom_ex_type', 'ex_verb_voice', 'context_r_pos',
                    'context_r_word', 'context_l_pos', 'context_l_word', 'deprel_to_parent']
            else:
                features = {args.featurestats}
            print "\n= DEPREP: {} =".format(dep)
            fs, fss, os = featurestats(lst['train'][dep] + lst['test'][dep], features=args.featurestats)
            if 'synt_path' in features:
                features.remove('synt_path')
                print "\n= synt path ="
                for it in fs['synt_path'].most_common(12):
                    print u"{} {}".format(it[0], it[1]).encode('utf-8')
                print "= Number of different features ="
                print len(fs['synt_path'])
                print "\n= For specific exptypes = "
                for exp in EXPTYPES:
                    print "\n= {} =".format(exp)
                    for it in fss[exp]['synt_path'].most_common(5):
                        print u"{} {}".format(it[0], it[1]).encode('utf-8')
                    print "= Number of different features ="
                    print len(fss[exp]['synt_path'])
                print "= Other counts ="
                for k, v in os.items():
                    print k, v

            print "\n= Other features ="
            for f in features:
                print "\n= {} =".format(f)
                print "Number of different features: ", len(fs[f])
                print u"Most common feature: {}".format(fs[f].most_common(1)).encode('utf-8')
                for exp in EXPTYPES:
                    print "Number of different features: ", len(fss[exp][f])
                    print "Most common feature: {}".format(fss[exp][f].most_common(1)).encode('utf-8')
                if f == 'dom_ex_type':
                    for it in fs['dom_ex_type'].most_common():
                        print u"{} {}".format(it[0], it[1]).encode('utf-8')

        
    if args.train or (args.eval and not (args.jtrain or args.loadmodels) ):
        print "= TRAINSET ="
        trainsentlst = createfile(opinionexp=False, opinionholder=True,
                devset=False if args.heldout else True, testset=False)
        dump_jsonfile(trainsentlst, DATA_PREFIX + '/out/' + 
                'heldouttrain' if args.heldout else 'dev' + "train.json")
        trainfilename = writeconll2009(trainsentlst, DATA_PREFIX + "/out/" +
                'heldouttrain.conll' if args.heldout else 'dev' + "train.conll")

    if args.test or (args.eval and not (args.jtest or args.loadmodels)):
        print "= TESTSET ="
        testsentlst = createfile(opinionexp=False, opinionholder=True,
                devset=False if args.heldout else True, testset=True) 
        dump_jsonfile(testsentlst, DATA_PREFIX + '/out/' + 
                'heldouttest' if args.heldout else 'dev' + "test.json")
        testfilename = writeconll2009(testsentlst, DATA_PREFIX + "/out/" +
                'heldouttest.conll' if args.heldout else 'dev' + "test.conll")

    if args.jtrain:
        print "= READ JSON ="
        trainfilename = DATA_PREFIX + "/out/" + 'heldouttrain.conll' if args.heldout else 'dev' + "train.conll"
        trainsentlst = read_jsonfile(args.jtrain)

    if args.jtest:
        testfilename = DATA_PREFIX + "/out/" + 'heldouttest.conll' if args.heldout else 'dev' + "test.conll"
        testsentlst = read_jsonfile(args.jtest)

    if args.iob2:
        print "= READ IOB2 ="
        tmp = readiob2(args.iob2)
        create_gates(tmp)
        testsentlst = jointestandresult(testsentlst,tmp)

    if args.eval and not args.lthsrl:
        print "= PARSE ="
        bohnetnivre = bohnet_nivre.Bohnet_Nivre()
        if not args.ctrain:
            bohnet_nivre_output = bohnetnivre.run(trainfilename)
        if not args.ctest:
            bohnet_nivre_output = bohnetnivre.run(testfilename)

    if args.eval and args.lthsrl:
        print "= PARSE ="
        lth_srl = lth_srl.Lth_srl()
        if not args.ctrain:
            writeconll(trainsentlst, trainfilename)
            lth_srl_output = lth_srl.run(trainfilename)
        if not args.ctest:
            lth_srl_output = lth_srl.run(testfilename)

    if args.ctrain:
        trainfilename = args.ctrain

    if args.ctest:
        testfilename = args.ctest

    if args.eval or args.stats:
        print "= EVAL ="
        trainsentlsts = {}
        testsentlsts = {}
        if args.lthsrl:
            trainsentlst = readconlltolst(trainsentlst, trainfilename + ".out")
            testsentlst = readconlltolst(testsentlst, testfilename + ".out")
            #print trainsentlst[0]
            #raise Exception
        else:
            for dr in DEPREPS:
                print "= DEPREP: {} =".format(dr)
                trainsentlsts[dr] = readconll2009tolst(trainsentlst, trainfilename + "." + dr)
                testsentlsts[dr] = readconll2009tolst(testsentlst, testfilename + "." + dr)
            

    #if args.run:
    #    print "Not implemented"

    if args.stats:
        if args.stats == "train":
            if trainsentlst:
                slst = trainsentlst
            slsts = trainsentlsts
        elif args.stats == "test":
            if testsentlst:
                slst = testsentlst
            slsts = testsentlsts
        if args.lthsrl:
            print_stats(trainsentlst, deprep='conll-lthsrl-wo-semantic')
        else:
            for dr in DEPREPS:
                print_stats(slsts[dr], deprep=dr)
        
    if args.eval:
        stats = {}
        if args.lthsrl:
            #dump_jsonfile(testsentlst, 'testsentlistdump.json')
            stats['notsem'] = print_eval(trainsentlst, testsentlst, semantic=False, loadmodels=args.loadmodels, savemodels=args.savemodels, deprep='conll-lthsrl-wo-semantic', predict=args.predict)
            stats['sem'] = print_eval(trainsentlst, testsentlst, semantic=True, loadmodels=args.loadmodels, savemodels=args.savemodels, deprep='conll-lthsrl-with-semantic', predict=args.predict)
        else:
            for dr in DEPREPS:
                stats[dr] = print_eval(trainsentlsts[dr], testsentlsts[dr], semantic=False, loadmodels=args.loadmodels, savemodels=args.savemodels, deprep=dr, predict=args.predict)

    if args.savejson:
        print "= SAVE JSON-FILE ="
        dump_jsonfile({'train': trainsentlsts, 'test': testsentlsts}, args.savejson)
        if stats:
            dump_jsonfile(stats, args.savejson + '.stats.json')

    if args.interactive:
        DEBUG = False
        DEBUGNOW = True
        print "Interactive"
        print args
        #test = "database.mpqa.2.0/docs/xbank/wsj_0768" # feil i opinion holder
        #test = "/out/eksempler-background.txt"
        #a = getopinionholder(test, examplerun=True)
        #a_iob2 = readiob2(DATA_PREFIX + '/out/wsj_0768.iob2')
        #create_gates(a_iob2)
        #3a_j = jointestandresult(a, a_dt)
        #a_dt = readconll2009tolst(a_j, DATA_PREFIX + '/out/wsj_0768.conll.dt')
        #f,l,s = getfeaturesandlabels(a_dt, semantic=False)
        ## lst = read_jsonfile(DATA_PREFIX + '/out/dev/gold_exp/goldex-o-new.json')
        #lst = lst['test']
        #f,l,s = getfeaturesandlabels(foo['train']['sb'], semantic=False)
        
        #minidevresult = readiob2(DATA_PREFIX + '/out/minidevresult.txt')
        ##minidevtest = createfile(opinionexp=False, opinionholder=True, doclistfile="/config/doclists/minitestset.txt")
        ##dump_jsonfile(minidevtest, DATA_PREFIX + '/out/minidevtest.txt')
        # minidevtest = read_jsonfile(DATA_PREFIX + "/out/minidevtest.txt", object_hook=pickle_object)
        # ##minidevtrain = createfile(opinionexp=False, opinionholder=True, doclistfile="/config/doclists/minitrainset.txt")
        # #minidevresult_copy = copy.deepcopy(minidevresult)
        # #create_gates(minidevresult_copy)
        # ##minidevresult_copy_sb = readconll2009tolst(minidevresult_copy, 'minidevtest.conll.sb')
        # #tlst = jointestandresult(minidevtest, minidevresult_copy)
        # minidevtrain = read_jsonfile(DATA_PREFIX + "/out/minidevtrain.json", object_hook=json_slice)
        # minidevtrain_sb = readconll2009tolst(minidevtrain, DATA_PREFIX + '/out/minidevtrain.conll.sb')
        # ##minidevtrain_dt = readconll2009tolst(minidevtrain, 'minidevtrain.conll.dt')
        # ##minidevtrain_conll = readconll2009tolst(minidevtrain, 'minidevtrain.conll.conll')
        # #minidevtest_sb = readconll2009tolst(tlst, 'minidevtest.conll.sb')
        # minidevtest_sb = readconll2009tolst(minidevtest, DATA_PREFIX + '/out/minidevtest.conll.sb')

        #minidevtest_sb = readconll2009tolst(minidevtest, 'minidevtest.conll.sb')
        #print_stats(minidevtest_sb, deprep='sb')

        #cleanupnonespanexpressions(testset)
        #cleanholdercandidates(testset)
        #cleanholders(testset)
        #cleanupnonespanexpressions(minidevtrain_sb)
        #cleanholdercandidates(minidevtrain_sb)
        #cleanholders(minidevtrain_sb)
        #
        #f,l,s = getfeaturesandlabels(minidevtrain_sb, semantic=False)
        #sent = minidevtest_sb[6]
        #sent = minidevtest[6]
        #ex = getexpressions_sent(sent)
        #ex = getexpressions_sent(sent, predict=False)
        #pex = getexpressions_sent(sent, predict=True)
        #holders = getholders_sent_new(sent)
        #hep = getholder_exp_pairs_sent(sent, ex, holders)

        #x = extolst(pex)
        #tf,tl,ts = getfeaturesandlabels(minidevtest_sb[0:10], semantic=False)
        #tf,tl,ts = getfeaturesandlabels(minidevtest_sb, semantic=False)
        #print_eval(minidevtrain_sb, minidevtest_sb, semantic=False)
        #print_eval(minidevtrain_sb, minidevtest_sb, semantic=False, predict=False)

        #trlst = read_jsonfile(DATA_PREFIX + '/out/holder/devtrain.json')
        #trlst_sb = readconll2009tolst(trlst, DATA_PREFIX + '/out/holder/devtrain.conll.sb')
        #telst = read_jsonfile(DATA_PREFIX + '/out/holder/devtest.json', object_hook=json_slice)
        #telst_sb = readconll2009tolst(telst, DATA_PREFIX + '/out/holder/devtest.conll.sb')
        #telst_dt = readconll2009tolst(telst, DATA_PREFIX + '/out/holder/devtest.conll.dt')
        #telst_conll = readconll2009tolst(telst, DATA_PREFIX + '/out/holder/devtest.conll.conll')
        #telst_srl = readconlltolst(telst, DATA_PREFIX + '/out/devtest.conll.out')
        #print_eval(trlst_sb, telst_sb, semantic=False)
        
        # lth = lth_srl.Lth_srl()
        #conlloutput = lth.run(DATA_PREFIX + "/out/tmp2.conll")
        #a = read_jsonfile(DATA_PREFIX + "/out/holder-trening.json")
        #a = [c[3]]
        #a = trainsentlst_conll
        #a = trainsentlst_dt
        #a = minidevtrain_dt
        ##ev = evaluate()
        #print_eval(trainsentlst_dt, testsentlst_dt, exptypes=['dse'], semantic=False)
        #print_eval(trainsentlst_dt, testsentlst_dt[0:10], exptypes=['ese'], semantic=False)
        #print_eval(trainsentlst_dt, testsentlst_dt[0:10], exptypes=['ose'], semantic=False)
    
        #a = copy.deepcopy(a_dt)
        
        #cleanupnonespanexpressions(telst_sb)
        #cleanholdercandidates(telst_sb)
        #cleanholders(telst_sb)
        #######b = a[3500]
        #semantic=False
        ########features, labels, stats = getfeaturesandlabels([b], exptype='ose', transitive=True)

        #print_eval(a, devtestset, semantic=False)
        #features, labels, stats = getfeaturesandlabels(a, transitive=True, semantic=semantic, predict=False)
        #vec, X, y = create_matrix(features['dse'], labels['dse'])
        #clf = create_model(X, y)
        ###
        ##devtestset = read_jsonfile(DATA_PREFIX + "/out/holder-test.json")
        ##devtestset = testsentlst_conll
        ##devtestset = testsentlst_dt
        #devtestset = a_dt
        #cleanupnonespanexpressions(devtestset)
        #cleanholdercandidates(devtestset)
        #cleanholders(devtestset)
        #ftest, ltest, stest = getfeaturesandlabels([devtestset[10]], transitive=True, semantic=semantic)
        #ftest, ltest, stest = getfeaturesandlabels(devtestset, transitive=True, semantic=semantic)
        # Xt, yt = transform_to_matrix(ftest['ese'], ltest['ese'], vec)
        # ###results = clf.predict(Xt)
        # #results = clf.predict_log_proba(Xt)
        # results = clf.predict_proba(Xt)

        # ##ev = evaluate_hc_tokens(results, yt)
        # #
        # ev = evaluate()
        # system_pairs = []
        # system_pairs.extend(ev.get_system_pairs(stest['positions']['ese'], results))
        # #for exp in EXPTYPES:
        # #    system_pairs.extend(eval.get_system_pairs(stest['positions'][exp], results))
        # ssc = ev.spansetcoverage_o_p(system_pairs, exptype='ese')
        # print "ssc: ", ssc

        
        #daughterlists_sent(b)
        #ex = getexpressions_sent(a[3500])
        #########restr = getholdercandidatesrestrictionset(ex)
        #holder_candidates = tagholdercandidates_sent(a[3500], ex)
        #count = 0
        #print len(telst_sb)
        #for sent in telst_sb:
        #    ex = getexpressions_sent(sent) 
        #    holder_dct = getholders_sent(sent)
        #    holder_exp_pairs = getholder_exp_pairs_sent(sent, ex, holder_dct)
        #    if holder_exp_pairs:
        #        #print holder_exp_pairs
        #        count += 1
                
        #g = getgraph_sent(b)
        #paths = getpaths_sent(g)
        ##daughterlists_sent(d)
        ##g2 = getgraph_sent(d)
        ##paths2 = getpaths_sent(g2)


        #find_ex_sent(a)
        #for i, t in enumerate(a[5364]): print i+1, t['form'], t['pos'], t['head'], 'DSE' if t['dse'] else ''

        #sent = a[5364]
        #SRI
        test = "database.mpqa.2.0/docs/20020510/21.50.13-28912" # SRI
        a = getopinionholder(test)
        # ###b = writeconll(a, DATA_PREFIX + "/out/tmp2.conll")
        # ### lth = lth_srl.Lth_srl()
        # ###conlloutput = lth.run(DATA_PREFIX + "/out/tmp2.conll")
        conlloutput = DATA_PREFIX + '/out/tmp2.conll.out'
        c = readconlltolst(a, conlloutput)
        sent = c[3]
        # ####foo = getfeaturesandlabels([a[5364]])
        daughterlists_sent(sent)
        ex = getexpressions_sent(sent)
        # tagholdercandidates_sent(sent, transitive=True) #False)
        # candidates = getholdercandidates_list_sent(sent)
        # ####print candidates
        holder_dct = getholders_sent_new(sent)
        # ####try:
        holder_exp_pairs = getholder_exp_pairs_sent(sent, ex, holder_dct)

        #print_tikzdep(sent)

        #s = ["Google is n't universally loved by newspaper execs and other content providers . ".split(), 
                     #"The bathroom was clean according to my husband .".split()]
        #f = io.open(DATA_PREFIX + "/out/eksempler-background.conll", 'w')
        #for sent in sents:
        #    for i, w in enumerate(sent):
        #        f.write(u"{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
        #            i+1,            # word id
        #            w,  # word form
        #            u"_", #token['lemma'], # gold lemma # 
        #            u"_",           # pred lemma
        #            u"_", #token['pos'],   # gold pos # 
        #            u"_",           # pred pos
        #            u"_",           # gold feat
        #            u"_",           # pred feat
        #            u"_",           # gold head
        #            u"_",           # pred head
        #            u"_",           # gold label
        #            u"_",           # pred label
        #            u"_"            # arg
        #            ))
        #    f.write(u"\n")
        #f.close()

        #sents = readconll2009(DATA_PREFIX + '/out/eksempler-background.conll.dt')
        #sents = readconll2009(DATA_PREFIX + '/out/eksempler-background.conll.sb')
        #print_tikzdep(sents[0])
        
        #a = [({4}, {1, 2, 3}, 'dse'), ({5}, 'implicit', 'dse')] 
        #b = [({4}, {1, 2, 3}, 'dse'), ({4,5}, 'implicit', 'dse')] 
        #c = [({4}, {1, 2, 3}, 'dse'), ({4}, 'implicit', 'dse'), ({6}, {1, 2, 3}, 'dse'), ({5, 6}, 'implicit', 'dse')] 
        #count_gold(a)
        #count_gold(b)
        #count_gold(c)
        #print counters
                    
        """

Out[99]: [({4}, {1, 2, 3}, 'dse'), ({5}, 'implicit', 'dse')]

In [76]: Interactive
1 Mugabe NNP 3 
2 's POS 1 
3 government NN 4 
4 dismissed VBD 0 DSE
5 criticism NN 4 DSE
6 of IN 5 
7 the DT 8 
8 election NN 6 
9 . . 4 
        """

        # He said that he liked ...
        # Se hvilket span som har størst overlapp
