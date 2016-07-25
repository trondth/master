#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict

from masters_project_config import *
from subprocess import Popen, PIPE, STDOUT
import re

lth_dir = DATA_PREFIX + '/lth_srl'

class Lth_srl:
    def run(self, conllfile, tagged=True):
        """
        @param conllfile conllfile
        @param tagged True if conllfile contains lemmas and pos-tags
        @return path to output file
        """
        p_run = Popen("sh scripts/run.sh < {} > {}.out".format(conllfile, conllfile), shell=True, cwd=lth_dir)
        p_run.communicate()[0]
        return conllfile + '.out'

if __name__ == "__main__":
    testconll = "devtest.conll"
    lthsrl = Lth_srl()
    outfile = lthsrl.run(testconll)
