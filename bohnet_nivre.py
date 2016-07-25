##!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict

from masters_project_config import *
from subprocess import Popen, PIPE, STDOUT
import re

models_dir = '/ltg/angelii/space_on_svn/angelii/PARSEABILITY/21_section/Bohnet_Nivre/parser/models/'
anna_dir = '/ltg/angelii/space_on_svn/angelii/PARSEABILITY/21_section/Bohnet_Nivre/parser/'
anna_jar = 'anna-3.3.jar'
bohnet_nivre_parser = 'is2.transitionR6j.Parser'
out = DATA_PREFIX + '/out/'
depreps = {
    'dt': 'dt-all-ptb_tok-ptb_pos.mdl',
    'sb': 'sb-all-ptb_tok-ptb_pos.mdl',
    'conll': 'conll-all-ptb_tok-ptb_pos.mdl'
    }

class Bohnet_Nivre:
    def run(self, conllfile):
        """
        @param conllfile conllfile
        @return path to output file
        """
        for dr, modelfile in depreps.items():
            cmd_str = "java -cp {}{} {} -model {}{} -beam 80 -test {} -out {}".format(anna_dir, anna_jar, bohnet_nivre_parser, models_dir, modelfile, conllfile, conllfile + '.' + dr)
            print cmd_str
            p_run = Popen(cmd_str, shell=True) #, cwd=lth_dir)
            p_run.communicate()[0]
        return conllfile, depreps.keys()

if __name__ == "__main__":
    testconll = "minidevresult.conll"
    bn = Bohnet_Nivre()
    outfile = bn.run(testconll)
