import sys,traceback
import os,stat
import time,datetime
import shutil
import json
import logging
import zlib

from inotifywrapper import InotifyWrapper
import _inotify as inotify


ES_DIR_NAME = "TEMP_ES_DIRECTORY"
UNKNOWN,JSD,STREAM,INDEX,FAST,SLOW,OUTPUT,STREAMERR,STREAMDQMHISTOUTPUT,INI,EOLS,EOR,COMPLETE,DAT,PDAT,PIDPB,PB,CRASH,MODULELEGEND,PATHLEGEND,BOX,BOLS,HLTRATES,HLTRATESLEGEND = range(24)            #file types 
TO_ELASTICIZE = [STREAM,INDEX,OUTPUT,STREAMERR,STREAMDQMHISTOUTPUT,EOLS,EOR,COMPLETE]
TEMPEXT = ".recv"
ZEROLS = 'ls0000'
STREAMERRORNAME = 'streamError'
STREAMDQMHISTNAME = 'streamDQMHistograms'

#Output redirection class
class stdOutLog:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)    
    def write(self, message):
        self.logger.debug(message)
class stdErrorLog:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    def write(self, message):
        self.logger.error(message)


    #on notify, put the event file in a queue
class MonitorRanger:

    def __init__(self,recursiveMode=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.eventQueue = False
        self.inotifyWrapper = InotifyWrapper(self,recursiveMode)

    def register_inotify_path(self,path,mask):
        self.inotifyWrapper.registerPath(path,mask)

    def start_inotify(self):
        self.inotifyWrapper.start()

    def stop_inotify(self):
        logging.info("MonitorRanger: Stop inotify wrapper")
        self.inotifyWrapper.stop()
        logging.info("MonitorRanger: Join inotify wrapper")
        self.inotifyWrapper.join()
        logging.info("MonitorRanger: Inotify wrapper returned")

    def process_default(self, event):
        self.logger.debug("event: %s on: %s" %(str(event.mask),event.fullpath))
        if self.eventQueue:
            self.eventQueue.put(event)

    def setEventQueue(self,queue):
        self.eventQueue = queue


class fileHandler(object):
    def __eq__(self,other):
        return self.filepath == other.filepath

    def __getattr__(self,name):
        if name not in self.__dict__: 
            if name in ["dir","ext","basename","name"]: self.getFileInfo() 
            elif name in ["filetype"]: self.filetype = self.getFiletype();
            elif name in ["run","ls","stream","index","pid"]: self.getFileHeaders()
            elif name in ["data"]: self.data = self.getData(); 
            elif name in ["definitions"]: self.getDefinitions()
            elif name in ["host"]: self.host = os.uname()[1];
        if name in ["ctime"]: self.ctime = self.getTime('c')
        if name in ["mtime"]: self.mtime = self.getTime('m')
        return self.__dict__[name]

    def __init__(self,filepath):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.filepath = filepath
        self.outDir = self.dir
        self.mergeStage = 0
        self.inputs = []

    def getTime(self,t):
        if self.exists():
            if t == 'c':
                dt=os.path.getctime(self.filepath)
            elif t == 'm':
                dt=os.path.getmtime(self.filepath)
            time = datetime.datetime.utcfromtimestamp(dt).isoformat() 
            return time
        return None   
                
    def getFileInfo(self):
        self.dir = os.path.dirname(self.filepath)
        self.basename = os.path.basename(self.filepath)
        self.name,self.ext = os.path.splitext(self.basename)

    def getFiletype(self,filepath = None):
        if not filepath: filepath = self.filepath
        filename = self.basename
        name,ext = self.name,self.ext
        name = name.upper()
        if "mon" not in filepath:
            if ext == ".dat" and "_PID" not in name: return DAT
            if ext == ".dat" and "_PID" in name: return PDAT
            if ext == ".ini" and "_PID" in name: return INI
            if ext == ".jsd" and "OUTPUT" in name: return JSD
            if ext == ".jsn":
                if STREAMERRORNAME.upper() in name: return STREAMERR
                elif "BOLS" in name : return BOLS
                elif "STREAM" in name and "_PID" in name: return STREAM
                elif "INDEX" in name and  "_PID" in name: return INDEX
                elif "CRASH" in name and "_PID" in name: return CRASH
                elif "EOLS" in name: return EOLS
                elif "EOR" in name: return EOR
        if ext==".jsn":
            if STREAMDQMHISTNAME.upper() in name and "_PID" not in name: return STREAMDQMHISTOUTPUT
            if "STREAM" in name and "_PID" not in name: return OUTPUT
            if "_HLTRATESLEGEND" in name: return  HLTRATESLEGEND
            elif "_HLTRATES" in name: return  HLTRATES
        if ext==".pb":
            if "_PID" not in name: return PB
            else: return PIDPB
        if name.endswith("COMPLETE"): return COMPLETE
        if ".fast" in filename: return FAST
        if "slow" in filename: return SLOW
        if ext == ".leg" and "MICROSTATELEGEND" in name: return MODULELEGEND
        if ext == ".leg" and "PATHLEGEND" in name: return PATHLEGEND
        if "boxes" in filepath : return BOX
        return UNKNOWN


    def getFileHeaders(self):
        filetype = self.filetype
        name,ext = self.name,self.ext
        splitname = name.split("_")
        if filetype in [STREAM,INI,PDAT,PIDPB,CRASH]: self.run,self.ls,self.stream,self.pid = splitname
        elif filetype == SLOW: self.run,self.ls,self.pid = splitname #this is wrong
        elif filetype == FAST: self.run,self.pid = splitname
        elif filetype in [DAT,PB,OUTPUT,STREAMERR,STREAMDQMHISTOUTPUT]: self.run,self.ls,self.stream,self.host = splitname
        elif filetype == INDEX: self.run,self.ls,self.index,self.pid = splitname
        elif filetype == EOLS: self.run,self.ls,self.eols = splitname
        elif filetype == HLTRATES:self.run,self.ls,self.ftype,self.pid = splitname
        else: 
            self.logger.warning("Bad filetype: %s" %self.filepath)
            self.run,self.ls,self.stream = [None]*3

    def getData(self):
        if self.ext == '.jsn': return self.getJsonData()
        elif self.filetype == BOX: return self.getBoxData()
        return None

    def getBoxData(self,filepath = None):
        if not filepath: filepath = self.filepath
        sep = '\n'
        try:
            with open(filepath,'r') as fi:
                data = fi.read()
                data = data.strip(sep).split(sep)
                data = dict([d.split('=') for d in data])
        except StandardError,e:
            self.logger.exception(e)
            data = {}


        return data

        #get data from json file
    def getJsonData(self,filepath = None):
        if not filepath: filepath = self.filepath
        try:
            with open(filepath) as fi:
                data = json.load(fi)
        except StandardError,e:
            self.logger.exception(e)
            data = {}
        except json.scanner.JSONDecodeError,e:
            self.logger.exception(e)
            data = None
        return data

    def setJsdfile(self,jsdfile):
        self.jsdfile = jsdfile
        if self.filetype in [OUTPUT,STREAMDQMHISTOUTPUT,CRASH,STREAMERR]: self.initData()
        
    def initData(self):
        defs = self.definitions
        self.data = {}
        if defs:
            self.data["data"] = [self.nullValue(f["type"]) for f in defs]

    def nullValue(self,ftype):
        if ftype == "integer": return "0"
        elif ftype  == "string": return ""
        else: 
            self.logger.warning("bad field type %r" %(ftype))
            return "ERR"

    def checkSources(self):
        data,defs = self.data,self.definitions
        for item in defs:
            fieldName = item["name"]
            index = defs.index(item)
            if "source" in item: 
                source = item["source"]
                sIndex,ftype = self.getFieldIndex(field)
                data[index] = data[sIndex]

    def getFieldIndex(self,field):
        defs = self.definitions
        if defs: 
            index = next((defs.index(item) for item in defs if item["name"] == field),-1)
            ftype = defs[index]["type"]
            return index,ftype

        
    def getFieldByName(self,field):
        index,ftype = self.getFieldIndex(field)
        data = self.data["data"]
        if index > -1:
            value = int(data[index]) if ftype == "integer" else str(data[index]) 
            return value
        else:
            self.logger.warning("bad field request %r in %r" %(field,self.definitions))
            return False

    def setFieldByName(self,field,value,warning=True):
        index,ftype = self.getFieldIndex(field)
        data = self.data["data"]
        if index > -1:
            data[index] = value
            return True
        else:
            if warning==True:
                self.logger.warning("bad field request %r in %r" %(field,self.definitions))
            return False

        #get definitions from jsd file
    def getDefinitions(self):
        if self.filetype in [STREAM]:
            self.jsdfile = self.data["definition"]
        elif not self.jsdfile: 
            self.logger.warning("jsd file not set")
            self.definitions = {}
            return False
        self.definitions = self.getJsonData(self.jsdfile)["data"]
        return True


    def deleteFile(self):
        #return True
        filepath = self.filepath
        self.logger.info(filepath)
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
            except Exception,e:
                self.logger.exception(e)
                return False
        return True

    def moveFile(self,newpath,copy = False,adler32=False):
        checksum=1
        if not self.exists(): return True,checksum
        oldpath = self.filepath
        newdir = os.path.dirname(newpath)

        if not os.path.exists(oldpath):
            self.logger.error("Source path does not exist: " + oldpath)
            return False,checksum

        self.logger.info("%s -> %s" %(oldpath,newpath))
        retries = 5
        newpath_tmp = newpath+TEMPEXT
        while True:
          try:
              if not os.path.isdir(newdir): os.makedirs(newdir)

              if adler32:checksum=self.moveFileAdler32(oldpath,newpath_tmp,copy)
              else:
                  if copy: shutil.copy(oldpath,newpath_tmp)
                  else: 
                      shutil.move(oldpath,newpath_tmp)
              break

          except (OSError,IOError),e:
              self.logger.exception(e)
              retries-=1
              if retries == 0:
                  self.logger.error("Failure to move file "+str(oldpath)+" to "+str(newpath_tmp))
                  return False,checksum
              else:
                  time.sleep(0.5)
        retries = 5
        while True:
        #renaming
            try:
                #shutil.move(newpath,newpath.replace(TEMPEXT,""))
                os.rename(newpath_tmp,newpath)
                break
            except (OSError,IOError),e:
                self.logger.exception(e)
                retries-=1
                if retries == 0:
                    self.logger.error("Failure to rename the temporary file "+str(newpath_tmp)+" to "+str(newpath))
                    return False,checksum
                else:
                    time.sleep(0.5)

        self.filepath = newpath
        self.getFileInfo()
        return True,checksum

    #move file (works only on src as file, not directory) 
    def moveFileAdler32(self,src,dst,copy):

        if os.path.isdir(src):
            raise Error("source `%s` is a directory")

        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        try:
            if os.path.samefile(src, dst):
                raise Error("`%s` and `%s` are the same file" % (src, dst))
        except OSError:
            pass

        #initial adler32 value
        adler32c=1
        #calculate checksum on the fly
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:

                length=16*1024
                while 1:
                    buf = fsrc.read(length)
                    if not buf:
                        break
                    adler32c=zlib.adler32(buf,adler32c)
                    fdst.write(buf)

        #copy mode bits on the destionation file
        st = os.stat(src)
        mode = stat.S_IMODE(st.st_mode)
        os.chmod(dst, mode)

        if copy==False:os.unlink(src)
        return adler32c

    def exists(self):
        return os.path.exists(self.filepath)

        #write self.outputData in json self.filepath
    def writeout(self,empty=False):
        filepath = self.filepath
        outputData = self.data
        self.logger.info(filepath)

        try:
            with open(filepath,"w") as fi:
                if empty==False:
                    json.dump(outputData,fi)
        except Exception,e:
            self.logger.exception(e)
            return False
        return True

    def esCopy(self):
        if not self.exists(): return
        if self.filetype in TO_ELASTICIZE:
            esDir = os.path.join(self.dir,ES_DIR_NAME)
            if os.path.isdir(esDir):
                newpath = os.path.join(esDir,self.basename)
                retries = 5
                while True:
                    try:
                        shutil.copy(self.filepath,newpath)
                        break
                    except (OSError,IOError),e:
                        self.logger.exception(e)
                        retries-=1
                        if retries == 0:
                            raise e
                        else:
                            time.sleep(0.5)


    def merge(self,infile):
        defs,oldData = self.definitions,self.data["data"][:]           #TODO: check infile definitions 
        jsdfile = infile.jsdfile
        host = infile.host
        newData = infile.data["data"][:]

        self.logger.debug("old: %r with new: %r" %(oldData,newData))
        result=Aggregator(defs,oldData,newData).output()
        self.logger.debug("result: %r" %result)
        self.data["data"] = result
        self.data["definition"] = jsdfile
        self.data["source"] = host

        if self.filetype==STREAMDQMHISTOUTPUT:
            self.inputs.append(infile)
        else:
            self.writeout()

    def updateData(self,infile):
        self.data["data"]=infile.data["data"][:]


class Aggregator(object):
    def __init__(self,definitions,newData,oldData):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.definitions = definitions
        self.newData = newData
        self.oldData = oldData

    def output(self):
        self.result = map(self.action,self.definitions,self.newData,self.oldData)
        return self.result

    def action(self,definition,data1,data2=None):
        actionName = "action_"+definition["operation"] 
        if hasattr(self,actionName):
            try:
                return getattr(self,actionName)(data1,data2)
            except AttributeError,e:
                self.logger.exception(e)
                return None
        else:
            self.logger.warning("bad operation: %r" %actionName)
            return None

    def action_binaryOr(self,data1,data2):
        try:
            res =  int(data1) | int(data2)
        except TypeError,e:
            self.logger.exception(e)
            res = 0
        return str(res)

    def action_merge(self,data1,data2):
        if not data2: return data1
        file1 = fileHandler(data1)
        
        file2 = fileHandler(data2)
        newfilename = "_".join([file2.run,file2.ls,file2.stream,file2.host])+file2.ext
        file2 = fileHandler(newfilename)

        if not file1 == file2:
            if data1: self.logger.warning("found different files: %r,%r" %(file1.filepath,file2.filepath))
            return file2.basename
        return file1.basename


    def action_sum(self,data1,data2):
        try:
            res =  int(data1) + int(data2)
        except TypeError,e:
            self.logger.exception(e)
            res = 0
        return str(res)

    def action_same(self,data1,data2):
        if str(data1) == str(data2):
            return str(data1)
        else:
            return "N/A"
        
    def action_cat(self,data1,data2):
        if data2 and data1: return str(data1)+","+str(data2)
        elif data1: return str(data1)
        elif data2: return str(data2)
        else: return ""

    def action_adler32(self,data1,data2):
        return "-1"

