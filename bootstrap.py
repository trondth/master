##!/usr/bin/env python
# -*- coding: utf-8 -*-

import random 
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
