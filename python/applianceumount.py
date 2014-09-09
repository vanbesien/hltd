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

sys.path.append('/opt/fff')


pidfile = '/var/run/fffumountwatcher.pid'

from setupmachine import FileManager

hltdconf='/etc/hltd.conf'
watch_directory='/fff/ramdisk'
machine_is_bu=False

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
        f.close()
    except Exception as ex:
        print "Unable to read watch_directory, using default: /fff/ramdisk"

def getTimeString():
    tzones = time.tzname
    if len(tzones)>1:zone=str(tzones[1])
    else:zone=str(tzones[0])
    return str(time.strftime("%H:%M:%S"))+" "+time.strftime("%d-%b-%Y")+" "+zone

def killPidMaybe():

    try:
        with open(pidfile,"r") as fi:
            pid=int(fi.read())
            try:
                os.kill(pid,0)
                print "process " + str(pid) + " is running\n"
                os.kill(pid,9)
                time.sleep(.1)
            except:
                print "process " + str(pid) + " is no running but pidfile present\n"
        os.unlink(pidfile)
    except:
        pass

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

def start():
    killPidMaybe()
    #double fork and exit

    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)
    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)
    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    with open(pidfile,"w+") as fi:
            fi.write(str(os.getpid()))

   parseConfiguration()

   if machine_is_bu==True:time.sleep(10)


def stop():
    killPidMaybe()
    parseConfiguration()
    if machine_is_bu==False:sys.exit(0)
    #continue with notifying FUs
    boxinfodir=os.path.join(watch_directory,'appliance/boxes')

    maxTimeout=120 #sec

    myhost = os.uname()[1]

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

        current_time = time.time()
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
        receiver.stop()
        receiver.join()

    receiver.stop()
    receiver.join()

    print "Finished FU suspend for:",machinelist-activeMachines
    if usedTimeout==maxTimeout:
        print "FU suspend failed for hosts:",activeMachines

def status():
    pass
