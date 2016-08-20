##!/usr/bin/env python
# -*- coding: utf-8 -*-

from opinionholder import *
import random 
VERBOSE = False

def prec_bootstrap(lst):
    psum = 0.0
    for p in lst:
        psum += p['p_sc']
    return psum / len(lst)

def rec_bootstrap(lst):
    rsum = 0.0
    for p in lst:
        rsum += p['r_sc']
    return rsum / len(lst)

def bootstrap(Xa, Xb, b=10000, t='prec'):
    
    """
    @return p-value
    """
    if len(Xa) != len(Xb):
        raise ValueError('Xa and Xb must be of equal length')

    ev = evaluate()
    
    # span coverages
    for p in Xa + Xb:
        if 'coref_gold' in p and len(p['coref_gold']) > 1:
            holder_gold = ev.check_coref(p['coref_gold'], p['holder_sys'])
        else:
            holder_gold = p['holder_gold']
        p['p_sc'] = ev.spancoverage(holder_gold, p['holder_sys'])
        p['r_sc'] = ev.spancoverage(p['holder_sys'], holder_gold)

    # delta
    prec_Xa = prec_bootstrap(Xa)
    prec_Xb = prec_bootstrap(Xb)
    rec_Xa = rec_bootstrap(Xa)
    rec_Xb = rec_bootstrap(Xb)
    delta = False
    if t == 'prec':
        delta = (prec_Xb - prec_Xa)
    elif t == 'rec':
        delta = (rec_Xb - rec_Xa)
    elif t == 'f':
        f_Xa = 2.0 * (prec_Xa * rec_Xa) / (prec_Xa + rec_Xa)
        f_Xb = 2.0 * (prec_Xb * rec_Xb) / (prec_Xb + rec_Xb)
        delta = f_Xb - f_Xa
    if isinstance(delta, bool):
        raise Exception('delta not found')

    x = []
    
    for i in range(b):
        x.append({'a': [], 'b': []})
        for rand_pair in range(len(Xa)):
            random_i = random.randrange(len(Xa))
            x[i]['a'].append(Xa[random_i])
            x[i]['b'].append(Xb[random_i])
        x[i]['prec_Xa'] = p_xa = prec_bootstrap(x[i]['a'])
        x[i]['prec_Xb'] = p_xb = prec_bootstrap(x[i]['b'])
        x[i]['rec_Xa'] = r_xa = rec_bootstrap(x[i]['a'])
        x[i]['rec_Xb'] = r_xb = rec_bootstrap(x[i]['b'])
        if t == 'prec':
            x[i]['delta'] = (x[i]['prec_Xb'] - x[i]['prec_Xa'])
        elif t == 'rec':
            x[i]['delta'] = (x[i]['rec_Xb'] - x[i]['rec_Xa'])
        elif t == 'f':
            if p_xa + r_xa == 0:
                f1 = 0.0
            else:
                f1 = 2.0 * (p_xa * r_xa) / (p_xa + r_xa)
            if p_xb + r_xb == 0:
                f2 = 0
            else:
                f2 = 2.0 * (p_xb * r_xb) / (p_xb + r_xb)
            x[i]['delta'] = f2 - f1

    s = 0
    for xi in x:
        if xi['delta'] > 2 * delta:
            s += 1

    if VERBOSE == 'vv':
        print "Delta: ", delta
        for i, xi in enumerate(x):
            print "\ndelta(x_" + str(i) + "): ", xi['delta']
            for k, v in sorted(xi.items()):
                print "\n", k
                if isinstance(v, list):
                    for it in v:
                        if 'p_sc' in it:
                            print it['p_sc']
                else:
                    print v
        print "\nPrec for Xa"
        for p in Xa:
            print p['p_sc']
        print "ssc: ", prec_Xa
        print "\nPrec for Xb"
        for p in Xb:
            print p['p_sc']
        print "ssc: ", prec_Xb
    #print "s: ", s
    #print "b: ", b
            #for k, v in sorted(xi.items()):
                #print "\n", k
                #if isinstance(v, list):
                #    for it in v:
                #        if 'p_sc' in it:
                #            print it['p_sc']
                #else:
                #    print v
    if VERBOSE:
        print "precision, b: ", prec_Xb
        print "precision, a: ", prec_Xa
        print "recall, b: ", rec_Xb
        print "recall, a: ", rec_Xa
        print "F, b: ", f_Xb
        print "F, a: ", f_Xa
        print "s: ", s
        print "b: ", b

    return float(s)/b
            
sp = {}
#spfolder = '/out/heldout'
spfolder = '/out/dev/exhfix-gold-restrict-sameexp'
#spfolder = '/out/exhfix-gold-restrict-sameexp'
sp['dt'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-dt.json')
sp['sb'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-sb.json')
sp['conll'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-conll.json')
#sp['dt-sameexp'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-dt.json')
#sp['sb-sameexp'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-sb.json')
#sp['conll-sameexp'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-conll.json')

#spfolder = '/out/exhfix-gold-restrict-sametype'
#sp['dt-sametype'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-dt.json')
#sp['sb-sametype'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-sb.json')
#sp['conll-sametype'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-conll.json')

#spfolder = '/out/exhfix-gold-restrict-all'
#sp['conll-all'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-conll.json')
#print len(sp['conll'])
VERBOSE = 'v'
print "=", spfolder, "="

if False:
    XB = sp['conll-sametype']
    XA = sp['conll-sameexp']
    print "= sameexp (best) mot sametype ="
    pvalue = bootstrap(XA, XB, b=10000, t='f')
    print "p-value: ", pvalue

if True:
    for dep in DEPREPS:
        for dep2 in DEPREPS:
            if dep != dep2:
                XA = sp[dep]
                XB = sp[dep2]
                print "= {} (best) mot {} =".format(dep2, dep)
                pvalue = bootstrap(XA, XB, b=10000, t='f')
                print "p-value: ", pvalue

#347
#518
#536
#657
#658
#792
#795
#796
#1369
#1370
#1372
#2329

#XA = sp['dt']#[112:117]
#XB = sp['conll']#[112:117]
#XA = sp['sb'][112:117]# [2305:2306]
#XB = sp['conll'][112:117]# [2302:2306] # 310 533 2235 2303
#XA = sp['dt'][1338:1343]
#XB = sp['conll'][1338:1343]
#
#VERBOSE = False
#pvalue = bootstrap(XA, XB, b=10000, t='prec')
#print "p-value: ", pvalue

#for i in range(len(XA)-6):
#    XA = sp['dt'][i:i+5]
#    XB = sp['conll'][i:i+5]
#    pvalue = bootstrap(XA, XB, b=10, t='prec')
#    if 0.2 < pvalue < 0.5:
#        pthisa = False
#        pthisb = False
#        for p in XA:
#            if 0 < p['p_sc'] < 1:
#                pthisa = True
#        for p in XB:
#            if 0 < p['p_sc'] < 1:
#                pthisb = True
#        if pthisa and pthisb:
#            print "p-value: ", pvalue, " - ", i
#XA = sp['sb'] # [:2000] # [112:117]
#XB = sp['conll'] # [:2000] # [112:117]
