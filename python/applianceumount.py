#!/bin/env python

import os,sys,socket
import subprocess
import shutil
import threading
import time
import cgitb
import CGIHTTPServer
import BaseHTTPServer

sys.path.append('/opt/fff')

from setupmachine import FileManager

hltdconf='/etc/hltd.conf'

watch_directory='/fff/ramdisk'
try:
    f=open(hltdconf)
    for l in f.readlines():
        ls=l.strip(' ')
        if not ls.startswith('#') and ls.startswith('watch_directory'):
            watch_directory=ls.split('=')[1].strip()
    f.close()
except Exception as ex:
    print "Unable to read watch_directory, using default: /fff/ramdisk"

boxinfodir=os.path.join(watch_directory,'appliance/boxes')

maxTimeout=120 #sec

myhost = os.uname()[1]

def getTimeString():
    tzones = time.tzname
    if len(tzones)>1:zone=str(tzones[1])
    else:zone=str(tzones[0])
    return str(time.strftime("%H:%M:%S"))+" "+time.strftime("%d-%b-%Y")+" "+zone

#disable the hltd service
hltdcfg = FileManager(hltdconf,'=',True,' ',' ')
hltdcfg.reg('enabled','False','[General]')
hltdcfg.commit()

#stop the service
p = subprocess.Popen("/sbin/service hltd stop", shell=True, stdout=subprocess.PIPE)
p.wait()

machinelist=[]
dirlist = os.listdir(boxinfodir)
for machine in dirlist:
    #skip self
    if machine == myhost:continue

    age = current_time - os.path.getmtime(os.path.join(boxinfodir,machine))
    print "found machine",machine," which is ",str(age)," seconds old"
    if age < 30:
        try:
            connection = httplib.HTTPConnection(machine, 8000,timeout=5)
            connection.request("GET",'cgi-bin/suspend_cgi.py')
            response = connection.getresponse()
            machinelist.append(machine)
        except:
            print "Unable to contact machine",machine
          #num_threads = nthreads 
 
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
            os.symlink('/opt/fff/cgi',watch_directory+'/cgi-bin')

            handler.cgi_directories = ['/cgi-bin']
            print("starting http server on port "+str(8005))
            self.httpd = BaseHTTPServer.HTTPServer(("", 8005), handler)

            self.httpd.serve_forever()
        except KeyboardInterrupt:
            return

    def stop(self):
            self.httpd.shutdown()

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
except:
    #handle interrupt
    print "Interrupted!"
    receiver.stop()
    receiver.join()

receiver.stop()
receiver.join()

print "Finished FU suspend for:",machinelist-activeMachines
if usedTimeout==maxTimeout:
    print "FU suspend failed for hosts:",activeMachines

