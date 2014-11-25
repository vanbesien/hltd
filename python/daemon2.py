import sys, os, time, atexit
import subprocess
from signal import SIGINT
from aUtils import * #for stdout and stderr redirection
import ConfigParser
import re

class Daemon2:
    """
    A generic daemon class.

    Usage: subclass the Daemon2 class and override the run() method

    reference:
    http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/

    attn: May change in the near future to use PEP daemon
    """

    def __init__(self, instance, processname, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
                      self.stdin = stdin
                      self.stdout = stdout
                      self.stderr = stderr
                      self.instance = instance
                      self.processname = processname

                      if instance=="main":
                          self.pidfile = '/var/run/hltd.pid'
                          self.conffile = '/etc/hltd.conf'
                          self.lockfile = '/var/lock/subsys/hltd'
                      else:
                          self.pidfile = "/var/run/hltd-"+instance+".pid"
                          self.conffile = "/etc/hltd-"+instance+".conf"
                          self.lockfile = '/var/lock/subsys/hltd-'+instance



    def daemonize(self):

        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                return -1
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

        # redirect standard file descriptors


        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        sys.stderr = stdErrorLog()
        sys.stdout = stdOutLog()

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)
        return 0

    def delpid(self):
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)
    def start(self):
        """
        Start the daemon
        """
        if not os.path.exists(self.conffile): raise Exception("Missing "+self.conffile)
        # Check for a pidfile to see if the daemon already runs

        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exists. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)
        # Start the daemon
        ret = self.daemonize()
        if ret == 0:
           self.run()
           ret = 0
        return ret

    def status(self):
        """
        Get the daemon status from the pid file and ps
        """
        retval = False
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if not pid:
            message = self.processname+" not running, no pidfile %s\n"
        else:
            try:
                os.kill(pid,0)
                message = self.processname+" is running with pidfile %s\n"
                retval = True
            except:
                message = self.processname+" pid exist in %s but process is not running\n"

        sys.stderr.write(message % self.pidfile)
        return retval

    def silentStatus(self):
        """
        Get the daemon status from the pid file and ps
        """
        retval = False
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if not pid:
            message = self.processname+" not running, no pidfile %s\n"
        else:
            try:
                os.kill(pid,0)
                retval = True
            except:
                pass

        return retval

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process
        try:
            # signal the daemon to stop
            timeout = 5.0 #kill timeout
            os.kill(pid, SIGINT)
            #Q: how is the while loop exited ???
            #A: os.kill throws an exception of type OSError
            #   when pid does not exist
            #C: not very elegant but it works
            while 1:
                if timeout <=0.:
                  sys.stdout.write("\nterminating with -9...")
                  os.kill(pid,9)
                  sys.stdout.write("\nterminated after 5 seconds\n")
                  #let system time to kill the process tree
                  time.sleep(0.5)
                  self.emergencyUmount()
                  time.sleep(0.5)
                os.kill(pid,0)
                sys.stdout.write('.')
                sys.stdout.flush()
                time.sleep(0.5)
                timeout-=0.5
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                #this handles the successful stopping of the daemon...
                if os.path.exists(self.pidfile):
                    print 'removing pidfile'
                    os.remove(self.pidfile)
                    sys.stdout.write('[OK]\n')
                    sys.stdout.flush()
            else:
                print str(err)
                sys.exit(1)
        sys.stdout.write('[OK]\n')

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        return self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon2. It will be called after the process has been
        daemonized by start() or restart().
        """

    def emergencyUmount(self):

        cfg = ConfigParser.SafeConfigParser()
        cfg.read(self.conffile)

        bu_base_dir=None#/fff/BU0?
        ramdisk_subdirectory = 'ramdisk'
        output_subdirectory = 'output'
       
        for sec in cfg.sections():
            for item,value in cfg.items(sec):
                if item=='ramdisk_subdiretory':ramdisk_subdirectory=value
                if item=='output_subdirectory':output_subdirectory=value
                if item=='bu_base_dir':bu_base_dir=value



        process = subprocess.Popen(['mount'],stdout=subprocess.PIPE)
        out = process.communicate()[0]
        mounts = re.findall('/'+bu_base_dir+'[0-9]+',out)
        mounts = list(set(mounts))
        for point in mounts:
            sys.stdout.write("trying emergency umount of "+point+"\n")
            try:
                subprocess.check_call(['umount','/'+point])
            except subprocess.CalledProcessError, err1:
                pass
            except Exception as ex:
                sys.stdout.write(ex.args[0]+"\n")
            try:
                subprocess.check_call(['umount',os.path.join('/'+point,ramdisk_subdirectory)])
            except subprocess.CalledProcessError, err1:
                sys.stdout.write("Error calling umount in cleanup_mountpoints\n")
                sys.stdout.write(str(err1.returncode)+"\n")
            except Exception as ex:
                sys.stdout.write(ex.args[0]+"\n")
            try:
                subprocess.check_call(['umount',os.path.join('/'+point,output_subdirectory)])
            except subprocess.CalledProcessError, err1:
                sys.stdout.write("Error calling umount in cleanup_mountpoints\n")
                sys.stdout.write(str(err1.returncode)+"\n")
            except Exception as ex:
                sys.stdout.write(ex.args[0]+"\n")


    def touchLockFile(self):
        try:
            with open(self.lockfile,"w+") as fi:
                pass
        except:
            pass

    def removeLockFile(self):
        try:
            os.unlink(self.lockfile)
        except:
            pass


 
