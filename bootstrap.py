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
        p['p_sc'] = ev.spancoverage(p['holder_gold'], p['holder_sys'])
        p['r_sc'] = ev.spancoverage(p['holder_sys'], p['holder_gold'])

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
        f1 = 2.0 * (prec_Xa * rec_Xa) / (prec_Xa + rec_Xa)
        f2 = 2.0 * (prec_Xb * rec_Xb) / (prec_Xb + rec_Xb)
        delta = f2 - f1
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

    if VERBOSE:
        print "Delta: ", delta
        for i, xi in enumerate(x):
            print "\ndelta(x_" + str(i) + "): ", xi['delta']
            #for k, v in sorted(xi.items()):
                #print "\n", k
                #if isinstance(v, list):
                #    for it in v:
                #        if 'p_sc' in it:
                #            print it['p_sc']
                #else:
                #    print v
    print "s: ", s
    print "b: ", b

    return float(s)/b
            
sp = {}
spfolder = '/out/heldout'
#spfolder = '/out/dev/exhfix-gold-restrict-sameexp'
sp['dt'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-dt.json')
sp['sb'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-sb.json')
sp['conll'] = read_jsonfile(DATA_PREFIX + spfolder + '/system_pairs-conll.json')

XA = sp['conll'] # [112:117]
XB = sp['sb'] # [112:117]
bootstrap = bootstrap(XA, XB, b=10000, t='f')
print "p-value: ", bootstrap
