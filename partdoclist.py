# For partitioning doclist.

from masters_project_config import *
from random import shuffle

import os.path

with open(DATA_PREFIX + config.get('doclist', 'PATH') +
          '/' + config.get('doclist', 'TRAINSET')) as f:
    filelist = [line[:-1] for line in f]

shuffle(filelist)

devtestlen = len(filelist)/10
devtestlist = sorted(filelist[0:devtestlen])
devtrainlist = sorted(filelist[devtestlen:])

devtrainfile = (DATA_PREFIX + config.get('doclist', 'DEVPATH') +
      '/' + config.get('doclist', 'DEVTRAINSET'))
if os.path.isfile(devtrainfile):
    print("Devtrainfile exists")
else:
    f = open(devtrainfile, 'w')
    for line in devtrainlist:
        f.write(line + '\n')
    f.close()

devtestfile = (DATA_PREFIX + config.get('doclist', 'DEVPATH') +
      '/' + config.get('doclist', 'DEVTESTSET'))
if os.path.isfile(devtestfile):
    print("Devtestfile exists")
else:
    f = open(devtestfile, 'w')
    for line in devtestlist:
        f.write(line + '\n')
    f.close()
    
