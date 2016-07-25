import ConfigParser
import os.path

PROJECTDIR = os.path.dirname(os.path.abspath(__file__))

if os.path.isfile(PROJECTDIR + '/masters_project.cfg'):
    CONFIGFILE = PROJECTDIR + '/masters_project.cfg'
else:
    CONFIGFILE = PROJECTDIR + '/masters_project-default.cfg'

#print CONFIGFILE

config = ConfigParser.ConfigParser()
config.read(CONFIGFILE)
DATA_PREFIX = config.get('general', 'DATA_PREFIX')

def getdoclist(filename):
    f = open(filename)
    l = f.read().splitlines()
    f.close()
    return l

DOCLIST_TRAINSET = getdoclist(DATA_PREFIX + config.get('doclist', 'PATH') +
                              '/' + config.get('doclist', 'TRAINSET'))
DOCLIST_TESTSET = getdoclist(DATA_PREFIX + config.get('doclist', 'PATH') + '/' + config.get('doclist', 'TESTSET'))

try:
    DOCLIST_DEVTRAINSET = getdoclist(DATA_PREFIX + config.get('doclist', 'DEVPATH') + '/' + config.get('doclist', 'DEVTRAINSET'))
    DOCLIST_DEVTESTSET = getdoclist(DATA_PREFIX + config.get('doclist', 'DEVPATH') + '/' + config.get('doclist', 'DEVTESTSET'))
except:
    print "feil"
