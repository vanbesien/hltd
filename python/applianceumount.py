#!/bin/env python

import os,sys,socket
import errno
import subprocess
import shutil
import threading
import time
import httplib
import cgitb
import CGIHTTPServer
import BaseHTTPServer
import syslog

hltdconf='/etc/hltd.conf'
watch_directory='/fff/ramdisk'
machine_is_bu=False
cgi_port=8000

def parseConfiguration():
    try:
        f=open(hltdconf)
        for l in f.readlines():
            ls=l.strip(' ')
            if not ls.startswith('#') and ls.startswith('watch_directory'):
                watch_directory=ls.split('=')[1].strip()
            if not ls.startswith('#') and ls.startswith('role'):
                if ls.split('=')[1].strip()=='bu': machine_is_bu=True
                if ls.split('=')[1].strip()=='fu': machine_is_fu=True
            if not ls.startswith('#') and ls.startswith('cgi_port'):
                cgi_port=int(ls.split('=')[1].strip())
        f.close()
    except Exception as ex:
        print "Unable to read watch_directory, using default: /fff/ramdisk"

class UmountResponseReceiver(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.httpd=None
 
    def run(self):

        try:
            cgitb.enable(display=0, logdir="/tmp")
            handler = CGIHTTPServer.CGIHTTPRequestHandler
            # the following allows the base directory of the http
            # server to be 'conf.watch_directory, which is writeable
            # to everybody
            os.chdir(watch_directory)
            os.remove('cgi-bin')
            #if os.path.exists(watch_directory+'/cgi-bin'):
            #    os.remove(watch_directory+'/cgi-bin')
            os.symlink('/opt/hltd/cgi',watch_directory+'/cgi-bin')

            handler.cgi_directories = ['/cgi-bin']
            print("starting http server on port "+str(cgi_port+5))
            self.httpd = BaseHTTPServer.HTTPServer(("", cgi_port+5), handler)

            self.httpd.serve_forever()
        except KeyboardInterrupt:
            return

    def stop(self):
            self.httpd.shutdown()

def stopFUs():
    parseConfiguration()
    if machine_is_bu==False:return True
    #continue with notifying FUs
    boxinfodir=os.path.join(watch_directory,'appliance/boxes')

    maxTimeout=120 #sec

    myhost = os.uname()[1]

    machinelist=[]
    dirlist = os.listdir(boxinfodir)
    for machine in dirlist:
        #skip self
        if machine == myhost:continue

        current_time = time.time()
        age = current_time - os.path.getmtime(os.path.join(boxinfodir,machine))
        print "found machine",machine," which is ",str(age)," seconds old"
        if age < 30:
            try:
                connection = httplib.HTTPConnection(machine, cgi_port,timeout=5)
                connection.request("GET",'cgi-bin/suspend_cgi.py')
                response = connection.getresponse()
                machinelist.append(machine)
            except:
                print "Unable to contact machine",machine
 

    receiver = UmountResponseReceiver()
    receiver.start()

    usedTimeout=0
    try:
        while usedTimeout<maxTimeout: 
            activeMachines=[]
            machinePending=False
            newmachinelist = os.listdir(boxinfodir)

            for machine in newmachinelist:

                if machine in machinelist:
                    machinePending=True
                    activeMachines.append(machine)

            if machinePending:
                usedTimeout+=2
                time.sleep(2)
                continue
            else:break
    except:
        #handle interrupt
        print "Interrupted!"
        syslog.syslog("hltd: FU suspend was interrupted")
        receiver.stop()
        receiver.join()
        return False

    receiver.stop()
    receiver.join()

    print "Finished FU suspend for:",machinelist-activeMachines
    if usedTimeout==maxTimeout:
        print "FU suspend failed for hosts:",activeMachines
        syslog.syslog("hltd: FU suspend failed for hosts"+str(activeMachines))
        return False

    return True

