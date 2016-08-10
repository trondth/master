##!/usr/bin/env python
# -*- coding: utf-8 -*-

from opinionholder import *
import random # > sign.

DEBUG = False
VERBOSE = True

def prec_bootstrap(lst):
    psum = 0.0
    for p in lst:
        psum += p['p_sc']
    return psum / len(lst)

def bootstrap(Xa, Xb, b=2):
    
    """
    @return p-value
    """
    if len(Xa) != len(Xb):
        raise ValueError('Xa and Xb must be of equal length')
    # span coverages
    for p in Xa + Xb:
        p['p_sc'] = ev.spancoverage(p['holder_gold'], p['holder_sys'])
        p['r_sc'] = ev.spancoverage(p['holder_sys'], p['holder_gold'])

    # delta
    prec_Xa = prec_bootstrap(Xa)
    prec_Xb = prec_bootstrap(Xb)
    delta = (prec_Xb - prec_Xa)

    x = []
    
    for i in range(b):
        x.append({'a': [], 'b': []})
        for rand_pair in range(len(Xa)):
            random_i = random.randrange(len(Xa))
            x[i]['a'].append(Xa[random_i])
            x[i]['b'].append(Xb[random_i])
        x[i]['prec_Xa'] = prec_bootstrap(x[i]['a'])
        x[i]['prec_Xb'] = prec_bootstrap(x[i]['b'])
        x[i]['delta'] = (x[i]['prec_Xb'] - x[i]['prec_Xa'])

    s = 0
    for xi in x:
        if xi['delta'] > 2 * delta:
            s += 1

    if VERBOSE:
        for i, xi in enumerate(x):
            print "\n\nX_" + str(i)
            for k, v in sorted(xi.items()):
                print "\n", k
                if isinstance(v, list):
                    for it in v:
                        if 'p_sc' in it:
                            print it['p_sc']
                else:
                    print v

    return float(s)/b
            
XA = sp['dt'][112:117]
XB = sp['conll'][112:117]
bootstrap = bootstrap(XA, XB)
print "p-value: ", bootstrap

def erroranalysis(lst, sp, deprlst=DEPREPS, best='sb', feature='synt_path', alld=False, threshold=0):
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
    counters['test'] += 1
    print counters
    pair = {}
    notbest = None
    if not alld:
        notbest = set(deprlst)
        notbest.discard(best)
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
        gold_dct[depr] = Counter()
        sys_dct[depr] = Counter()
        freqtable_labels.append('gold_' + depr)
        if feature == 'synt_path' or feature == 'holder_length':
            freqtable.extend([[] for i in range(2)])
            freqtable_labels.append('sys_' + depr)
        else:
            freqtable.extend([[] for i in range(1)])
    freqtable.extend([[],[]])
    #print freqtable
    #print deprlst
    if deprlst == DEPREPS:
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
            _erroranalysis_pair(lst, pair, gold_dct, sys_dct, deprlst, freqtable, freqtable_labels, best, notbest, ev, feature=feature, alld=alld, threshold=threshold)
    elif deprlst == ['conll', 'srl']:
        for pair['srl'] in sp['srl']:
            # unødv. kompleks
            for pair['conll'] in sp['conll']:
                if (pair['srl']['holder_gold'] == pair['conll']['holder_gold'] and 
                    pair['srl']['exp'] == pair['conll']['exp'] and
                    pair['srl']['sent'] == pair['conll']['sent']):
                    _erroranalysis_pair(lst, pair, gold_dct, sys_dct, deprlst, freqtable, freqtable_labels, best, notbest, ev, feature=feature, alld=alld, threshold=threshold)
    return gold_dct, sys_dct, freqtable, freqtable_labels

def _erroranalysis_pair(lst, pair, gold_dct, sys_dct, deprlst, freqtable, freqtable_labels, best, notbest, ev, feature=None, alld=False, threshold=0):
    error_pair = False
    if DEBUG and pair['conll']['sent'] == 528:
        print pair
    sc = {}
    sc_rev = {}
    for depr in deprlst:
        sc[depr] = ev.spancoverage(pair[depr]['holder_sys'], pair[depr]['holder_gold'])
        sc_rev[depr] = ev.spancoverage(pair[depr]['holder_gold'], pair[depr]['holder_sys'])
        if sc[depr] != sc_rev[depr]:
            counters['partial_span' + depr] += 1
        if DEBUG and pair['conll']['sent'] == 528:
            print pair
            print sc, alld
        if pair[depr]['holder_gold'] == 'w':
            counters['tmp'] += 1
            tmpstr = depr, pair[depr]['holder_gold'], pair[depr]['holder_sys']
    if alld:
        _erroranalysis_pair_stats(sc, sc_rev, threshold=threshold)
        error_pair = _erroranalysis_all(sc)
        if error_pair:
            counters['error_pairs'] += 1
    else:
        error_pair = _erroranalysis_better(sc, best, notbest)
        if pair['sb']['holder_gold'] == 'w' and error_pair:
            print error_pair
            print tmpstr
            print pair['conll']['sent']
        if DEBUG and pair['conll']['sent'] == 528:
            print error_pair
            
    #print pair
    #raise
    #if pair['sent'] == 439:
    #    print pair
    if error_pair:
        counters['errorpairs'] += 1
        
        # w/imp must be checked in another way
        #wimp_pair = set()
        #wimp_syspair = set()
        #for i, depr in enumerate(deprlst):
        #    if (isinstance(pair[depr]['holder_gold'], basestring)):
        #        if pair[depr]['holder_gold'] == 'w':
        #            counters['holder_gold - w - ' + depr ] += 1
        #        else:
        #            counters['holder_gold - imp - ' + depr ] += 1
        #        wimp_pair.add(depr)
        #    elif (isinstance(pair[depr]['holder_sys'], basestring)):
        #        if pair[depr]['holder_sys'] == 'w':
        #            counters['holder_sys - w - ' + depr ] += 1
        #        else:
        #            counters['holder_sys - imp - ' + depr ] += 1
        #        counters['holder_sys - w/imp - ' + depr] += 1
        #        wimp_syspair.add(depr)

        if True:
            #print pair['conll']['holder_sys'], pair['conll']['holder_gold']
            freqtable[-1].append(pair[best]['sent'])
            freqtable[-2].append(pair[best]['exp'])
            for i, depr in enumerate(deprlst):
                sent = lst[depr][pair[depr]['sent']]
                ex_id = getex_head(pair[depr]['exp'], sent)
                g_id = False
                if not isinstance(pair[depr]['holder_gold'], basestring):
                    g_id = getex_head(pair[depr]['holder_gold'], sent)
                s_id = False
                if not isinstance(pair[depr]['holder_sys'], basestring):
                    s_id = getex_head(pair[depr]['holder_sys'], sent)
                if feature == 'holder_head_pos':
                    if g_id:
                        g_head_pos_str = sent[g_id-1]['pos']
                    else:
                        g_head_pos_str = "n/a ({})".format(pair[depr]['holder_gold'])
                    if s_id:
                        s_head_pos_str = sent[s_id-1]['pos']
                    else:
                        s_head_pos_str = "n/a ({})".format(pair[depr]['holder_sys'])
                    gold_dct[depr][g_head_pos_str] += 1
                    sys_dct[depr][s_head_pos_str] += 1
                    freqtable[i*2].append(g_head_pos_str)
                    freqtable[i*2+1].append(s_head_pos_str)
                if feature == 'ex_head_pos':
                    ex_head_pos_str = sent[ex_id-1]['pos']
                    gold_dct[depr][ex_head_pos_str] += 1
                    freqtable[i].append(ex_head_pos_str)
                if feature == 'deprel_to_parent':
                    deprel_to_parent_str = sent[ex_id-1]['deprel']
                    gold_dct[depr][deprel_to_parent_str] += 1
                    freqtable[i].append(deprel_to_parent_str)
                if feature == 'holder_length':
                    gold_dct[depr][len(pair[depr]['holder_gold'])] += 1
                    sys_dct[depr][len(pair[depr]['holder_sys'])] += 1
                    freqtable[i*2].append(len(pair[depr]['holder_gold']))
                    freqtable[i*2+1].append(len(pair[depr]['holder_sys']))
                if feature == 'dom_ex_type':
                    try:
                        dom_ex_type_str = dom_ex_type(sent, sent[ex_id-1]['head'])
                        gold_dct[depr][dom_ex_type_str] += 1
                        freqtable[i].append(dom_ex_type_str)
                    except:
                        raise Exception('need tagged sent lst with dse/ese/ose')
                if feature == 'synt_path':
                    daughterlists_sent(sent)
                    if g_id:
                        g_synt_path = syntactic_path(g_id, ex_id, sent)
                    else:
                        g_synt_path = "n/a ({})".format(pair[depr]['holder_gold'])
                    if s_id:
                        s_synt_path = syntactic_path(s_id, ex_id, sent)
                    else:
                        s_synt_path = "n/a ({})".format(pair[depr]['holder_sys'])
                    freqtable[i*2].append(g_synt_path)
                    freqtable[i*2+1].append(s_synt_path)
                    sys_dct[depr][s_synt_path] += 1
                    gold_dct[depr][g_synt_path] += 1
    return gold_dct, sys_dct, freqtable, freqtable_labels
                    
def erroranalysis_print_dct(dct, deprlst=DEPREPS, n=10):
    if n == False:
        n = None
    for depr in deprlst:
        print "\n= {} =".format(depr)
        for k,v in dct[depr].most_common(n):
            print k, "\t", v
    #    print "\n\n{}\n".format(depr)
    #    for t in reversed(dct[depr].items()):
    #        print u"{}\t{}".format(t[0], t[1])

def erroranalysis_print_table(freqtable, freqtable_labels, n=10):
    if n == False:
        n = 10
    for i in freqtable_labels:
        print u"{}\t".format(i),
    for i in range(len(freqtable[0][:n])):
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

    @param freqtable 
    """
    count = 0
    #for c in range(len(freqtable[-1])):
    #    # sent nr
    #    print c
    #    # sent
    #    p = sp
    #    sent = deplst[int(p['sent'])+ 1]
    #    for i, t in enumerate(sent):
    #        if i+1 in p['exp']:
    #            print "[{}]".format(t['form']),
    #        elif not isinstance(p['holder_gold'], basestring) and i+1 in p['holder_gold']:
    #            print "_{}_".format(t['form']),
    #        elif False and not isinstance(p['holder_sys'], basestring) and i+1 in p['holder_sys']:
    #            print "S{}S".format(t['form']),
    #        else:
    #            print "{}".format(t['form']),
    #    # conll path

    #    
    #    print freqtable[0][c], freqtable[-1][c]
        
    for p in sp:
        if (count < len(freqtable[-1]) and freqtable[-1][count] == p['sent']
            and freqtable[-2][count] == p['exp']):
            # sent nr
            print "\n\n{}\n".format(p['sent']),
            for i, t in enumerate(deplst[p['sent']]):
                # sent
                try:
                    if i+1 in p['exp']:
                        print "[{}]".format(t['form']),
                    elif not isinstance(p['holder_gold'], basestring) and i+1 in p['holder_gold']:
                        print u"{{{}}}".format(t['form']),
                    elif False and not isinstance(p['holder_sys'], basestring) and i+1 in p['holder_sys']:
                        print u"S{}S".format(t['form']),
                    else:
                        print u"{}".format(t['form']),
                except:
                    print p
                    raise
            # path
            #print "\n"
            #for i, t in enumerate(deplst[p['sent']]):
                #print t['head'],
            # synt_path path
            print ""
            print "\n", freqtable[4][count]
            print "\n"
            count += 1

#def _erroranalysis_sort_dct(dct, deprlst=DEPREPS):
#    return_dct = {}
#    for depr in deprlst:
#        return_dct[depr] = OrderedDict(sorted(dct[depr].iteritems(), key=lambda k: k[1]))
#    return return_dct

def _erroranalysis_better(sc, best, notbest, threshold=0):
    if threshold == 0:
        for depr in notbest:
            if sc[depr] > threshold:
                return False
            if sc[best] <= threshold:
                return False
    else:
        print "Threshold not implemented."
        for depr in notbest:
            if sc[depr] >= sc[best]:
                return False
    return True

#tmpcnt = Counter()

def _erroranalysis_pair_stats(sc, sc_rev, threshold=0):
    counters['pairs total'] += 1
    correct = "pairs found with\t"
    if threshold == 0:
        for dep, v in sorted(sc.items()):
            if v > 0:
                correct += str(dep) + '/'
    else:
        for depv, deprv in itertools.izip(sorted(sc.items()), sorted(sc_rev.items())):
            dep, v = depv
            dep_rev, v_rev = deprv
            if v != v_rev:
                counters['partial_span2' + dep] += 1
            #if counters['pairs total'] > 20: raise
            if v > threshold and v_rev > threshold:
                #print v,v_rev
                correct += str(dep) + '/'
    if correct == "pairs found with\t":
        correct += "None"
    counters[correct] += 1

def _erroranalysis_all(sc, threshold=0):
    for i, v in enumerate(sc.values()):
        if v > threshold:
            return False
    return True

def print_counters():
    print "= Counters ="
    print "Span coverage threshold: ", args.threshold
    for k,v in sorted(counters.items(), key=lambda x: x[0]):
        print k, "\t", v

def print_synt(lst, sent):
    for c, w in enumerate(lst[sent]):
        print c+1, "\t", w['head'], "\t", w['deprel'], "\t", w['form']

def print_exps_in_s(lst, sent, pairs):
    for pair in pairs:
        #print pair['sent']
        if pair['sent'] == sent:
            print pair['exp']

def print_synt_ex(lst, sent, ex, pairs):
    p = False
    for pair in pairs:
        if pair['sent'] == sent:
            print pair
            print str(pair['exp'])
            print str(pair['exp']) == ex
            if str(pair['exp']) == ex:
                print pair
                p = pair
    if not p:
        print pair['exp']
        print ex
        raise
    for c, w in enumerate(lst[sent]):
        hs = True
        hg = True
        if isinstance(p['holder_sys'], basestring):
            hs = False
        if isinstance(p['holder_gold'], basestring):
            hg = False
        try:
            if hs and hg and c+1 in p['holder_sys'] and c+1 in p['holder_gold']:
                print u'{}\t{}\t{}\t{}\t{}'.format(c+1, w['head'], w['deprel'], w['form'], 'H_g+s')
            elif hs and c+1 in p['holder_sys']:
                print u'{}\t{}\t{}\t{}\t{}'.format(c+1, w['head'], w['deprel'], w['form'], 'H_s')
            elif hg and c+1 in p['holder_gold']:
                print u'{}\t{}\t{}\t{}\t{}'.format(c+1, w['head'], w['deprel'], w['form'], 'H_g')
            elif c+1 in p['exp']:
                print u'{}\t{}\t{}\t{}\t{}'.format(c+1, w['head'], w['deprel'], w['form'], 'EXP')
            else:
                print u'{}\t{}\t{}\t{}\t{}'.format(c+1, w['head'], w['deprel'], w['form'], '')
        except:
            print p, w
            raise
            
if __name__ == "__main__":
    counters.clear()
    print "= Erroranalysis ="
    sp = {}
    deplst = {}
    spfolder = '/out/dev/exhfix-gold-restrict-sameexp'

    #lst = read_jsonfile(DATA_PREFIX + spfolder + '/gold-restrict-sameexp-exheadfix.json')
    #lst = lst['test']
    sp['dt'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-dt.json')
    print len(sp['dt'])
    sp['sb'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-sb.json')
    sp['conll'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-conll.json')
    # # #sp['srl'] = read_jsonfile(DATA_PREFIX + '/out/dev/gold_exp/system_pairs-conll-lthsrl-wo-semantic.json')
    deplst['dt'] = readconll2009(DATA_PREFIX + '/out/devtest.conll.dt')
    deplst['sb'] = readconll2009(DATA_PREFIX + '/out/devtest.conll.sb')
    deplst['conll'] = readconll2009(DATA_PREFIX + '/out/devtest.conll.conll')
    # # # deplst['srl'] = readconll(DATA_PREFIX + '/out/devtest.conll.out')
    # # #gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, deprlst=['conll', 'srl'], best='srl') #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos) synt_path
    #gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, alld=True, feature='synt_path')# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-spfiles')
    argparser.add_argument('-conllfiles')
    argparser.add_argument('-i', action='store_true')
    argparser.add_argument('-synt')
    argparser.add_argument('-feature')
    argparser.add_argument('-best')
    argparser.add_argument('-sys_cnt', action='store_true')
    argparser.add_argument('-gold_cnt', action='store_true')
    argparser.add_argument('-print_table', action='store_true')
    argparser.add_argument('-n', type=int)
    argparser.add_argument('-dump')
    argparser.add_argument('-t', '--threshold', type=float, default=0)
    argparser.add_argument('-count', action='store_true')
    argparser.add_argument('-print_s', type=int)
    argparser.add_argument('-print_ex')
    argparser.add_argument('-deprellst')
    argparser.add_argument('-print_dep', default='conll')
    #args = argparser.parse_args(args=['-dump', 'sents'])
    #args = argparser.parse_args(args=['-i'])
    #args = argparser.parse_args(args=['-count', '-t', '0.99'])
    #args = argparser.parse_args(args=['-count'])
    args = argparser.parse_args(args=[
        #'-gold_cnt',
        #'-sys_cnt',
        #'-print_table',
        ##'-n', '8',
        #'-feature', 'synt_path',
        #'-feature', 'deprel_to_parent',
        #'-feature', 'dom_ex_type',
        #'-feature', 'holder_length',
        #'-t', '0.99',
        #'-count'
        #'-deprellst', 'dt',
        #'-best', 'conll',
        ##'-best', 'none',
        #'-print_s', '8', # NMOD
        #'-print_s', '588', # P
        #'-print_ex', 'set([2])', # P
        #'-print_s', '1235',
        #'-print_ex', 'set([11])',
        ##'-print_ex', 'set([5, 6, 7, 8, 9, 10])',
        #'-print_dep', 'conll'
        ])

    #for i in range(50):
    #    print i
    #    print print_exps_in_s(deplst['dt'], i, sp['dt'])

    if args.deprellst:
        deprlst = args.deprellst.split(',')
    else:
        deprlst = DEPREPS

    #if args.feature:
    #    if args.deprellst:
    #        gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, alld=False, best='conll', feature=args.feature, threshold=args.threshold, deprlst=deprlst)# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)
    #    else:
    #        gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, alld=False, best='conll', feature=args.feature, threshold=args.threshold)# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)

    if args.synt:
        print_synt(deplst['conll'], args.synt)

    #Single sent
    if args.print_s and args.print_ex:
        print_synt_ex(deplst[args.print_dep], args.print_s, args.print_ex, sp[args.print_dep])
    if args.print_s:
        print_exps_in_s(deplst[args.print_dep], args.print_s, sp[args.print_dep])

    #Count
    if args.count:
        gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, best='conll', alld=True, feature='synt_path', threshold=args.threshold)# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)
        print_counters()

    # all wrong
    if args.best == 'none':
        gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, best='conll', alld=True, feature='synt_path', threshold=args.threshold)# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)

    # conll best
    if args.dump == 'sents' or (args.feature == 'synt_path' and args.best == 'conll'):
        gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, alld=False, best='conll', feature=args.feature, threshold=args.threshold)# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)

    # dt best
    #gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, alld=False, best='dt', feature='synt_path', threshold=0.99)# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)

    # sb best
    #gdct, sdct, freqtable, freqtable_labels = erroranalysis(deplst, sp, alld=False, best='sb', feature='synt_path', threshold=0.99)# feature='holder_head_pos') #, alld=True) #alld=True)#, feature='holder_head_pos') #, feature='ex_head_pos)

    if args.gold_cnt:
        print "= Most common errors, gold holder ="
        erroranalysis_print_dct(gdct, n=args.n, deprlst=deprlst)
    if args.sys_cnt:
        print "= Most common errors, system holder ="
        erroranalysis_print_dct(sdct, n=args.n, deprlst=deprlst)
    if args.print_table:
        print erroranalysis_print_table(freqtable, freqtable_labels, n=args.n)
    if args.dump:
        print erroranalysis_print_tagged_sentences(freqtable, deplst['conll'], sp['conll'])
    #print erroranalysis_print_tagged_sentences(freqtable, deplst['sb'], sp['sb'])
    #print argmaxcxh(holder_dct['peep'], candidates['dse'])
    #print cand_in_ghodct(list(candidates['dse'])[1], holder_dct['peep'])
    

    ##find ex sentence, stats
    #for i, s in enumerate(deplst['dt']):
    #    last = False
    #    for w in s:
    #        if last and last['form'] == 'has' and w['pos'][0] == 'V':
    #            print i, ": ", 
    #            for w2 in s:
    #                print w2['form'],
    #            print ""
    #            for h2 in s:
    #                print h2['head'],
    #            print ""
    #        last = w

#137 :  She added that the Argentine government has declared a 30-day emergency . 

    #lsts = read_jsonfile(DATA_PREFIX + spfolder + '/gold-r-sameex.json')
    #snum = 284
    #for p in sp['dt']:
    #    if p['sent'] == snum:
    #        print p
            
    """
    {u'confidence': 0.9551899339110933, u'exptype': u'dse', u'holder_gold': set([1]), u'holder_sys': set([1]), u'exp': set([3, 4]), u'coref_gold': [set([1])], u'sent': 272}
    {u'confidence': 0.8635499674787045, u'exptype': u'dse', u'holder_gold': set([1]), u'holder_sys': set([1]), u'exp': set([13, 14, 15]), u'coref_gold': [set([1])], u'sent': 272}
    {u'confidence': 0.787190238504431, u'exptype': u'ese', u'holder_gold': set([1]), u'holder_sys': set([1]), u'exp': set([10, 11]), u'coref_gold': [set([1])], u'sent': 272}
    """
                
    #for i, w in enumerate(deplst['dt'][snum]):
    #    print "", i+1, w['form'], w['head']
    #    
    #for i, w in enumerate(deplst['sb'][snum]):
    #    print "", i+1, w['form'], w['head']

    #for i, w in enumerate(deplst['conll'][272]):
    #    print "", i+1, w['form'], w['head']

            
                
    #print_tikzdep(deplst['sb'][1235])
    
    # 348 - holder er en konjunksjon
    # 531

    #for i in range(len(freqtable[0])):
    #    #counters['test'] += 1
    #    if (freqtable[1][i][1] == '/' and freqtable[3][i][1] == '/'
    #            and freqtable[5][i][1] == '/' and freqtable[0][i][1] == '/'):
    #        counters['all_sys_wrong_imp'] += 1

    #    #if (freqtable[1][i] == 'n/a (implicit)' and
    #    #        freqtable[3][i] == 'n/a (implicit)' and
    #    #        freqtable[5][i] == 'n/a (implicit)'):
    #    #    counters['all_sys_wrong_imp'] += 1
    

    ##foo = ev.spansetcoverage_o_p_l(XA, exptype='dt', length=8)
    #for p in XA + XB:
    #    p['p_sc'] = ev.spancoverage(p['holder_gold'], p['holder_sys'])
    #    p['r_sc'] = ev.spancoverage(p['holder_sys'], p['holder_gold'])

    #print "DT:"
    #for p in XA: print p['r_sc']
    #print "CD:"
    #for p in XB: print p['r_sc']

    #psum_XA = 0.0
    #for p in XA: psum_XA += p['p_sc']
    #prec_XA = psum_XA/len(p)

    #psum_XB = 0.0
    #for p in XB: psum_XB += p['p_sc']
    #prec_XB = psum_XB/len(p)

    #delta = abs(prec_XA - prec_XB)

