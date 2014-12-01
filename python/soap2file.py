#!/bin/env python
#
# chkconfig:   2345 81 03
#

import os
import pwd
import sys
import SOAPpy
import time

sys.path.append('/opt/hltd/python')
sys.path.append('/opt/hltd/lib')

import demote
import hltdconf
from daemon2 import Daemon2


def writeToFile(filename,content,overwrite):
    try:
        os.stat(filename)
        #file exists
        if overwrite=="False":return
    except:
        pass
    try:
        with open(filename,'w') as file:
            file.write(content)
        return "Success"
    except IOError as ex:
        return "Failed to write data: "+str(ex)


def createDirectory(dirname):
    try:
        os.mkdir(dirname)
        return "Success"
    except OSError as ex:
        return "Failed to create directory: "+str(ex)


class Soap2file(Daemon2):

    def __init__(self):
        Daemon2.__init__(self,'soap2file','main','hltd')
        #SOAPpy.Config.debug = 1
        self._conf=hltdconf.hltdConf('/etc/hltd.conf')
        self._hostname = os.uname()[1]

    def run(self):
        dem = demote.demote(self._conf.user)
        dem()

        server = SOAPpy.SOAPServer((self._hostname, self._conf.soap2file_port))
        server.registerFunction(writeToFile)
        server.registerFunction(createDirectory)
        server.serve_forever()


if __name__ == "__main__":

    soap2file = Soap2file()

    if len(sys.argv) == 2:

        if 'start' == sys.argv[1]:

            try:
                soap2file.start()
                time.sleep(.1)
                if soap2file.silentStatus():
                    print '[OK]'
                else:
                    print '[Failed]'
                    sys.exit(1)
            except Exception as ex:
                print ex
                sys.exit(1)

        elif 'stop' == sys.argv[1]:
            soap2file.stop()
            soap2file.delpid()

        elif 'restart' == sys.argv[1]:

            try:
                soap2file.restart()
                time.sleep(.1)
                if soap2file.silentStatus():
                    print '[OK]'
                else:
                    print '[Failed]'
                    sys.exit(1)
            except Exception as ex:
                print ex
                sys.exit(1)

        elif 'status' == sys.argv[1]:
            soap2file.status()

        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart|status" % sys.argv[0]
        sys.exit(2)

