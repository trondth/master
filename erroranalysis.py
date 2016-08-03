##!/usr/bin/env python
# -*- coding: utf-8 -*-

from opinionholder import *

DEBUG = False

def erroranalysis(lst, sp, deprlst=DEPREPS, best='sb', feature='synt_path', alld=False):
    """
    @param lst list of sentences with list of tokens
    @param sp list of system pairs (output from eval)
    @param feature feature, for erroranalysis 
    @alld if set, then we will check where all depreps make errors
    @best check when the other depreps guess wrong and best guesses correct
    @return 4-tuple with gold counts, system counts, freqtable and freqtable labels
    """
    # Sjekk de tilfellene der best gjør det bedre enn de andre
    #print feature
    pair = {}
    notbest = None
    if not alld:
        notbest = set(deprlst)
        notbest.remove(best)
        print "= Compare pairs where {} guesses correct and the others wrong =".format(best)
    else:
        print "= Investigate pairs where all representations guess wrong ="
        print deprlst
    ev = evaluate()
    freqtable = []
    freqtable_labels = []
    gold_dct = {}
    sys_dct = {}
    for depr in deprlst:
        gold_dct[depr] = OrderedDict()
        sys_dct[depr] = OrderedDict()
        freqtable_labels.append('gold_' + depr)
        if feature == 'synt_path':
            freqtable.extend([[] for i in range(2)])
            freqtable_labels.append('sys_' + depr)
        else:
            freqtable.extend([[] for i in range(1)])
    freqtable.extend([[]])
    #print freqtable
    #print deprlst
    if deprlst == DEPREPS:
        print len(sp['dt'])
        print len(sp['sb'])
        print len(sp['conll'])
        for pair['dt'], pair['sb'], pair['conll'] in itertools.izip(sp['dt'], sp['sb'], sp['conll']):
            if (pair['dt']['exp'] != pair['sb']['exp'] or
                    pair['conll']['exp'] != pair['sb']['exp'] or
                    pair['conll']['exp'] != pair['dt']['exp']):
                counters['errors'] += 1
            else:
                counters['total number of pairs'] += 1
            if DEBUG and pair['conll']['sent'] == 59:
                print "PAIR", pair
                for i, t in enumerate(lst['sb'][59]):
                    print i+1, t['head'], t['form'], t['pos']
            _erroranalysis_pair(lst, pair, gold_dct, sys_dct, deprlst, freqtable, freqtable_labels, best, notbest, ev, feature=feature, alld=alld)
    elif deprlst == ['conll', 'srl']:
        for pair['srl'] in sp['srl']:
            # unødv. kompleks
            for pair['conll'] in sp['conll']:
                if (pair['srl']['holder_gold'] == pair['conll']['holder_gold'] and 
                    pair['srl']['exp'] == pair['conll']['exp'] and
                    pair['srl']['sent'] == pair['conll']['sent']):
                    _erroranalysis_pair(lst, pair, gold_dct, sys_dct, deprlst, freqtable, freqtable_labels, best, notbest, ev, feature=feature, alld=alld)
    return _erroranalysis_sort_dct(gold_dct, deprlst=deprlst), _erroranalysis_sort_dct(sys_dct, deprlst=deprlst), freqtable, freqtable_labels

def _erroranalysis_pair(lst, pair, gold_dct, sys_dct, deprlst, freqtable, freqtable_labels, best, notbest, ev, feature=None, alld=False):
    error_pair = False
    if DEBUG and pair['conll']['sent'] == 528:
        print pair
    sc = {}
    for depr in deprlst:
        sc[depr] = ev.spancoverage(pair[depr]['holder_sys'], pair[depr]['holder_gold'])
        if DEBUG and pair['conll']['sent'] == 528:
            print sc, alld
    if alld:
        error_pair = _erroranalysis_all(sc)
        if error_pair:
            counters['error_pairs'] += 1
    else:
        error_pair = _erroranalysis_better(sc, best, notbest)
        if DEBUG and pair['conll']['sent'] == 528:
            print error_pair
            
    if error_pair:

        # w/imp must be checked in another way
        wimp_pair = False
        for i, depr in enumerate(deprlst):
            if (isinstance(pair[depr]['holder_gold'], basestring)):
                if i == 0:
                    counters['holder_gold - w/imp - ' + depr] += 1
                wimp_pair = True
            elif (isinstance(pair[depr]['holder_sys'], basestring)):
                counters['holder_sys - w/imp - ' + depr] += 1
                wimp_pair = True

        if not wimp_pair:
            freqtable[-1].append(pair[best]['sent'])
            for i, depr in enumerate(deprlst):
                sent = lst[depr][pair[depr]['sent']]
                ex_id = getex_head(pair[depr]['exp'], sent)
                g_id = getex_head(pair[depr]['holder_gold'], sent)
                s_id = getex_head(pair[depr]['holder_sys'], sent)
                if feature == 'holder_head_pos':
                    g_head_pos_str = sent[g_id-1]['pos']
                    gold_dct[depr][g_head_pos_str] = gold_dct[depr].get(g_head_pos_str, 0) + 1
                    s_head_pos_str = sent[s_id-1]['pos']
                    sys_dct[depr][s_head_pos_str] = gold_dct[depr].get(s_head_pos_str, 0) + 1
                    freqtable[i*2].append(g_head_pos_str)
                    freqtable[i*2+1].append(s_head_pos_str)
                if feature == 'ex_head_pos':
                    ex_head_pos_str = sent[ex_id-1]['pos']
                    if ex_head_pos_str in gold_dct[depr]:
                        gold_dct[depr][ex_head_pos_str] += 1
                    else:
                        gold_dct[depr][ex_head_pos_str] = 1
                    freqtable[i].append(ex_head_pos_str)
                if feature == 'deprel_to_parent':
                    deprel_to_parent_str = sent[ex_id-1]['deprel']
                    if deprel_to_parent_str in gold_dct[depr]:
                        gold_dct[depr][deprel_to_parent_str] += 1
                    else:
                        gold_dct[depr][deprel_to_parent_str] = 1
                    freqtable[i].append(deprel_to_parent_str)
                if feature == 'synt_path':
                    daughterlists_sent(sent)
                    s_synt_path = syntactic_path(s_id, ex_id, sent)
                    g_synt_path = syntactic_path(g_id, ex_id, sent)
                    freqtable[i*2].append(g_synt_path)
                    freqtable[i*2+1].append(s_synt_path)
                    if s_synt_path in sys_dct[depr]:
                        sys_dct[depr][s_synt_path] += 1
                    else:
                        sys_dct[depr][s_synt_path] = 1
                    if g_synt_path in gold_dct[depr]:
                        gold_dct[depr][g_synt_path] += 1
                    else:
                        gold_dct[depr][g_synt_path] = 1
    return gold_dct, sys_dct, freqtable, freqtable_labels
                    
def erroranalysis_print_dct(dct, deprlst=DEPREPS):
    for depr in deprlst:
        print "\n\n{}\n".format(depr)
        for t in reversed(dct[depr].items()):
            print u"{}\t{}".format(t[0], t[1])

def erroranalysis_print_table(freqtable, freqtable_labels):
    for i in freqtable_labels:
        print u"{}\t".format(i),
    for i in range(len(freqtable[0])):
        print ""
        for col in freqtable:
            try:
                print u"{}\t".format(col[i]),
            except:
                print "feil: "
                print col
                print i
                raise

def erroranalysis_print_tagged_sentences(freqtable, deplst, sp):
    """
    In google docs, regex replace G(\w*)G to {$1}

    @param freqtable Bla bla
    """
    count = 0
    for p in sp:
        if count < len(freqtable[-1]) and freqtable[-1][count] == p['sent']:
            print "\n{}\t".format(p['sent']),
            for i, t in enumerate(deplst[p['sent']]):
                if i+1 in p['exp']:
                    print "[{}]".format(t['form']),
                elif i+1 in p['holder_gold']:
                    print "G{}G".format(t['form']),
                elif i+1 in p['holder_sys']:
                    print "S{}S".format(t['form']),
                else:
                    print "{}".format(t['form']),
            count += 1
        elif count >= len(freqtable[-1]):
            print count
            print freqtable[-1][-1]

def _erroranalysis_sort_dct(dct, deprlst=DEPREPS):
    return_dct = {}
    for depr in deprlst:
        return_dct[depr] = OrderedDict(sorted(dct[depr].iteritems(), key=lambda k: k[1]))
    return return_dct

def _erroranalysis_better(sc, best, notbest):
    for depr in notbest:
        if sc[depr] >= sc[best]:
            return False
    return True

#tmpcnt = Counter()

def _erroranalysis_all(sc, threshold=0):
    for i, v in enumerate(sc.values()):
        if v > threshold:
            return False
    return True

def print_counters():
    print "= Counters ="
    for k,v in counters.items():
        print k, v
            
if __name__ == "__main__":
    counters.clear()
    print "= Erroranalysis ="
    #stats_srl = read_jsonfile(DATA_PREFIX + '/out/2016-06-21-dump.json.stats.json')
    sp = {}
    deplst = {}
    spfolder = '/out/dev/gold-restrict-sametype-json'
    sp['dt'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-dt.json')
    sp['sb'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-sb.json')
    sp['conll'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-conll.json')
    # # #sp['srl'] = read_jsonfile(DATA_PREFIX + '/out/dev/gold_exp/system_pairs-conll-lthsrl-wo-semantic.json')
    deplst['dt'] = readconll2009(DATA_PREFIX + '/out/devtest.conll.dt')
    deplst['sb'] = readconll2009(DATA_PREFIX + '/out/devtest.conll.sb')
    deplst['conll'] = readconll2009(DATA_PREFIX + '/out/devtest.conll.conll')
    # # # deplst['srl'] = readconll(DATA_PREFIX + '/out/devtest.conll.out')
    # # #gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, deprlst=['conll', 'srl'], best='srl') #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos) synt_path
    #gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, alld=True, feature='synt_path')# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)
    #gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, best='conll', alld=False, feature='synt_path')# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)

    gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, alld=True, feature='deprel_to_parent')# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)

    print_counters()

    #erroranalysis_print_dct(gdct)
    #erroranalysis_print_dct(sdct)
    #print erroranalysis_print_table(freqtable, freqtable_labels)
    #print erroranalysis_print_tagged_sentences(freqtable, deplst['sb'], sp['sb'])
    #print erroranalysis_print_tagged_sentences(freqtable, deplst['sb'], sp['sb'])
    #print argmaxcxh(holder_dct['peep'], candidates['dse'])
    #print cand_in_ghodct(list(candidates['dse'])[1], holder_dct['peep'])
    

            
                
    
