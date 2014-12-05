#!/bin/env python

import os,sys,socket
import shutil
import json
import subprocess
import shutil

import time

sys.path.append('/opt/hltd/python')
#from fillresources import *

#for testing enviroment
try:
    import cx_Oracle
except ImportError:
    pass
try:
    import MySQLdb
except ImportError:
    pass


backup_dir = '/opt/fff/backup'
try:
    os.makedirs(backup_dir)
except:pass

hltdconf = '/etc/hltd.conf'
busconfig = '/etc/appliance/bus.config'
elasticsysconf = '/etc/sysconfig/elasticsearch'
elasticconf = '/etc/elasticsearch/elasticsearch.yml'

dbhost = 'empty'
dbsid = 'empty'
dblogin = 'empty'
dbpwd = 'empty'
equipmentSet = 'latest'
minidaq_list = ["bu-c2f13-21-01","bu-c2f13-23-01","bu-c2f13-25-01","bu-c2f13-27-01",
                "fu-c2f13-17-01","fu-c2f13-17-02","fu-c2f13-17-03","fu-c2f13-17-04"
                "fu-c2f13-19-01","fu-c2f13-19-02","fu-c2f13-19-03","fu-c2f13-19-04"]
dqm_list = ["bu-c2f13-31-01","fu-c2f13-39-01","fu-c2f13-39-02",
            "fu-c2f13-39-03","fu-c2f13-39-04"]
ed_list = ["bu-c2f13-29-01","fu-c2f13-41-01","fu-c2f13-41-02",
           "fu-c2f13-41-03","fu-c2f13-41-04"]
myhost = os.uname()[1]

def getmachinetype():

    #print "running on host ",myhost
    if   myhost.startswith('dvrubu-') or myhost.startswith('dvfu-') : return 'daq2val','fu'
    elif myhost.startswith('dvbu-') : return 'daq2val','bu'
    elif myhost.startswith('bu-') : return 'daq2','bu'
    elif myhost.startswith('fu-') : return 'daq2','fu'
    elif myhost.startswith('cmsdaq-401b28') : return 'test','fu'
    elif myhost.startswith('dvfu-') : return 'test','fu'
    else: 
       print "debug"
       return 'unknown','unknown'
    

def getIPs(hostname):
    try:
        ips = socket.gethostbyname_ex(hostname)
    except socket.gaierror, ex:
        print 'unable to get ',hostname,'IP address:',str(ex)
        raise ex
    return ips

def getTimeString():
    tzones = time.tzname
    if len(tzones)>1:zone=str(tzones[1])
    else:zone=str(tzones[0])
    return str(time.strftime("%H:%M:%S"))+" "+time.strftime("%d-%b-%Y")+" "+zone


def checkModifiedConfigInFile(file):

    f = open(file)
    lines = f.readlines(2)#read first 2
    f.close()
    tzones = time.tzname
    if len(tzones)>1:zone=tzones[1]
    else:zone=tzones[0]

    for l in lines:
        if l.strip().startswith("#edited by fff meta rpm at "+getTimeString()):
            return True
    return False
    


def checkModifiedConfig(lines):
    for l in lines:
        if l.strip().startswith("#edited by fff meta rpm at "+getTimeString()):
            return True
    return False
    

def getBUAddr(parentTag,hostname):

    global equipmentSet
    #con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_W/'+dbpwd+'@'+dbhost+':10121/int2r_lb.cern.ch',
    #equipmentSet = 'eq_140325_attributes'

    if env == "vm":
        con = MySQLdb.connect( host= dbhost, user = dblogin, passwd = dbpwd, db = dbsid)
    else:
        if parentTag == 'daq2':
            if dbhost.strip()=='null':
                #con = cx_Oracle.connect('CMS_DAQ2_HW_CONF_W','pwd','cms_rcms',
                con = cx_Oracle.connect(dblogin,dbpwd,dbsid,
                          cclass="FFFSETUP",purity = cx_Oracle.ATTR_PURITY_SELF)
            else:
                con = cx_Oracle.connect(dblogin+'/'+dbpwd+'@'+dbhost+':10121/'+dbsid,
                          cclass="FFFSETUP",purity = cx_Oracle.ATTR_PURITY_SELF)
        else:
            con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_W/'+dbpwd+'@int2r2-v.cern.ch:10121/int2r_lb.cern.ch',
                          cclass="FFFSETUP",purity = cx_Oracle.ATTR_PURITY_SELF)
    
    #print con.version

    cur = con.cursor()

    #IMPORTANT: first query requires uppercase parent eq, while the latter requires lowercase

    qstring=  "select attr_name, attr_value from \
                DAQ_EQCFG_HOST_ATTRIBUTE ha, \
                DAQ_EQCFG_HOST_NIC hn, \
                DAQ_EQCFG_DNSNAME d \
                where \
                ha.eqset_id=hn.eqset_id AND \
                hn.eqset_id=d.eqset_id AND \
                ha.host_id = hn.host_id AND \
                ha.attr_name like 'myBU%' AND \
                hn.nic_id = d.nic_id AND \
                d.dnsname = '" + hostname + "' \
                AND d.eqset_id = (select eqset_id from DAQ_EQCFG_EQSET \
                where tag='"+parentTag.upper()+"' AND \
                ctime = (SELECT MAX(CTIME) FROM DAQ_EQCFG_EQSET WHERE tag='"+parentTag.upper()+"')) order by attr_name"

    qstring2= "select attr_name, attr_value from \
                DAQ_EQCFG_HOST_ATTRIBUTE ha, \
                DAQ_EQCFG_HOST_NIC hn, \
                DAQ_EQCFG_DNSNAME d \
                where \
                ha.eqset_id=hn.eqset_id AND \
                hn.eqset_id=d.eqset_id AND \
                ha.host_id = hn.host_id AND \
                ha.attr_name like 'myBU%' AND \
                hn.nic_id = d.nic_id AND \
                d.dnsname = '" + hostname + "' \
                AND d.eqset_id = (select child.eqset_id from DAQ_EQCFG_EQSET child, DAQ_EQCFG_EQSET \
                parent WHERE child.parent_id = parent.eqset_id AND parent.cfgkey = '"+parentTag+"' and child.cfgkey = '"+ equipmentSet + "')"

    #NOTE: to query squid master for the FU, replace 'myBU%' with 'mySquidMaster%'

    if equipmentSet == 'latest':
      cur.execute(qstring)
    else:
      print "query equipment set",parentTag+'/'+equipmentSet
      #print '\n',qstring2
      cur.execute(qstring2)

    retval = []
    for res in cur:
        retval.append(res)
    cur.close()
    #print retval
    return retval


def getSelfDataAddr(parentTag):


    global equipmentSet
    #con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_W/'+dbpwd+'@'+dbhost+':10121/int2r_lb.cern.ch',
    #equipmentSet = 'eq_140325_attributes'

    con = cx_Oracle.connect(dblogin+'/'+dbpwd+'@'+dbhost+':10121/'+dbsid,
                        cclass="FFFSETUP",purity = cx_Oracle.ATTR_PURITY_SELF)
    #print con.version

    cur = con.cursor()

    hostname = os.uname()[1]

    qstring1= "select dnsname from DAQ_EQCFG_DNSNAME where dnsname like '%"+os.uname()[1]+"%' \
                AND d.eqset_id = (select child.eqset_id from DAQ_EQCFG_EQSET child, DAQ_EQCFG_EQSET \
                parent WHERE child.parent_id = parent.eqset_id AND parent.cfgkey = '"+parentTag+"' and child.cfgkey = '"+ equipmentSet + "')"

    qstring2 = "select dnsname from DAQ_EQCFG_DNSNAME where dnsname like '%"+os.uname()[1]+"%' \
                AND eqset_id = (select child.eqset_id from DAQ_EQCFG_EQSET child, DAQ_EQCFG_EQSET parent \
                WHERE child.parent_id = parent.eqset_id AND parent.cfgkey = '"+parentTag+"' and child.cfgkey = '"+ equipmentSet + "')"


    if equipmentSet == 'latest':
        cur.execute(qstring1)
    else:
        print "query equipment set (data network name): ",parentTag+'/'+equipmentSet
        #print '\n',qstring2
        cur.execute(qstring2)

    retval = []
    for res in cur:
        if res[0] != os.uname()[1]+".cms": retval.append(res[0])
    cur.close()

    if len(retval)>1:
        for r in res:
            #prefer .daq2 network if available
            if r.startswith(os.uname()[1]+'.daq2'): return [r]

    return retval

def getInstances(hostname):
    #instance.input example:
    #{"cmsdaq-401b28.cern.ch":{"names":["main","ecal"],"sizes":[40,20]}} #size is in megabytes
    #BU can have multiple instances, FU should have only one specified. If none, any host is assumed to have only main instance
    try:
       with open('/opt/fff/instances.input','r') as fi:
           doc = json.load(fi)
           return doc[hostname]['names'],doc[hostname]['sizes']
    except:
        return ["main"],0


class FileManager:
    def __init__(self,file,sep,edited,os1='',os2=''):
        self.name = file
        f = open(file,'r')
        self.lines = f.readlines()
        f.close()
        self.sep = sep
        self.regs = []
        self.remove = []
        self.edited = edited
        #for style
        self.os1=os1
        self.os2=os2

    def reg(self,key,val,section=None):
        self.regs.append([key,val,False,section])

    def removeEntry(self,key):
        self.remove.append(key)

    def commit(self):
        out = []
        if self.edited  == False:
            out.append('#edited by fff meta rpm\n')

        #first removing elements
        for rm in self.remove:
            for i,l in enumerate(self.lines):
                if l.strip().startswith(rm):
                    del self.lines[i]
                    break

        for i,l in enumerate(self.lines):
            lstrip = l.strip()
            if lstrip.startswith('#'):
                continue
                   
            try:
                key = lstrip.split(self.sep)[0].strip()
                for r in self.regs:
                    if r[0] == key:
                        self.lines[i] = r[0].strip()+self.os1+self.sep+self.os2+r[1].strip()+'\n'
                        r[2]= True
                        break
            except:
                continue
        for r in self.regs:
            if r[2] == False:
                toAdd = r[0]+self.os1+self.sep+self.os2+r[1]+'\n'
                insertionDone = False
                if r[3] is not None:
                    for idx,l in enumerate(self.lines):
                        if l.strip().startswith(r[3]):
                            try:
                                self.lines.insert(idx+1,toAdd)
                                insertionDone = True
                            except:
                                pass
                            break
                if insertionDone == False:
                    self.lines.append(toAdd)
        for l in self.lines:
            out.append(l)
        #print "file ",self.name,"\n\n"
        #for o in out: print o
        f = open(self.name,'w+')
        f.writelines(out)
        f.close()


def restoreFileMaybe(file):
    try:
        try:
            f = open(file,'r')
            lines = f.readlines()
            f.close()
            shouldCopy = checkModifiedConfig(lines)
        except:
            #backup also if file got deleted
            shouldCopy = True

        if shouldCopy:
            print "restoring ",file
            backuppath = os.path.join(backup_dir,os.path.basename(file))
            f = open(backuppath)
            blines = f.readlines()
            f.close()
            if  checkModifiedConfig(blines) == False and len(blines)>0:
                shutil.move(backuppath,file)
    except Exception, ex:
        print "restoring problem: " , ex
        pass

#main function
if __name__ == "__main__":
    argvc = 1
    if not sys.argv[argvc]:
        print "selection of packages to set up (hltd and/or elastic) missing"
        sys.exit(1)
    selection = sys.argv[argvc]
    #print selection

    if 'restore' in selection:
        if 'hltd' in selection:
            restoreFileMaybe(hltdconf)
        if 'elasticsearch' in selection:
            restoreFileMaybe(elasticsysconf)
            restoreFileMaybe(elasticconf)
        if 'hltd' in selection:
            try:
                os.remove(os.path.join(backup_dir,os.path.basename(busconfig)))
            except:
                pass
        sys.exit(0)

    argvc += 1
    if not sys.argv[argvc]:
        print "Enviroment parameter missing"
        sys.exit(1)
    env = sys.argv[argvc]

    argvc += 1
    if not sys.argv[argvc]:
        print "global elasticsearch URL name missing"
        sys.exit(1)
    elastic_host = sys.argv[argvc]
    #http prefix is required here
    if not elastic_host.strip().startswith('http://'):
        elastic_host = 'http://'+ elastic_host.strip()
        #add default port name for elasticsearch
    if len(elastic_host.split(':'))<3:
        elastic_host+=':9200'

    argvc += 1
    if not sys.argv[argvc]:
        print "CMSSW base missing"
        sys.exit(1)
    cmssw_base = sys.argv[argvc]

    argvc += 1
    if not sys.argv[argvc]:
        print "DB connection hostname missing"
        sys.exit(1)
    dbhost = sys.argv[argvc]

    argvc += 1
    if not sys.argv[argvc]:
        print "DB connection SID missing"
        sys.exit(1)
    dbsid = sys.argv[argvc]

    argvc += 1
    if not sys.argv[argvc]:
        print "DB connection login missing"
        sys.exit(1)
    dblogin = sys.argv[argvc]

    argvc += 1
    if not sys.argv[argvc]:
        print "DB connection password missing"
        sys.exit(1)
    dbpwd = sys.argv[argvc]

    argvc += 1
    if not sys.argv[argvc]:
        print "equipment set name missing"
        sys.exit(1)
    if sys.argv[argvc].strip() != '':
        equipmentSet = sys.argv[argvc].strip()

    argvc += 1
    if not sys.argv[argvc]:
        print "CMSSW job username parameter is missing"
        sys.exit(1)
    username = sys.argv[argvc]

    argvc+=1
    if not sys.argv[argvc]:
        print "CMSSW number of threads/process is missing"
    nthreads = sys.argv[argvc]


    argvc+=1
    if not sys.argv[argvc]:
        print "CMSSW number of framework streams/process is missing"
    nfwkstreams = sys.argv[argvc]



    argvc+=1
    if not sys.argv[argvc]:
        print "CMSSW log collection level is missing"
    cmsswloglevel =  sys.argv[argvc]

    cluster,type = getmachinetype()
    #override for daq2val!
    #if cluster == 'daq2val': cmsswloglevel =  'INFO'
    if env == "vm":
        cnhostname = os.uname()[1]
    else:
        cnhostname = os.uname()[1]+'.cms'
       
    use_elasticsearch = 'True'
    cmssw_version = 'CMSSW_7_1_4_patch1'
    dqmmachine = 'False'
    execdir = '/opt/hltd'
    resourcefract = '0.5'

    if cluster == 'daq2val':
        runindex_name = 'dv'        
    elif cluster == 'daq2':
        runindex_name = 'cdaq'
        if myhost in minidaq_list:
            runindex_name = 'minidaq'
        if myhost in dqm_list or myhost in ed_list:

            use_elasticsearch = 'False'
            runindex_name = 'dqm'
            cmsswloglevel = 'DISABLED'
            dqmmachine = 'True'
            username = 'dqmpro'
            resourcefract = '1.0'
            cmssw_version = ''
            if type == 'fu':
                cmsswloglevel = 'ERROR'
                cmssw_base = '/home/dqmprolocal'
                execdir = '/home/dqmprolocal/output' ##not yet
        if myhost in ed_list:
            runindex_name = 'ed'
            username = 'dqmdev'
            if type == 'fu':
                cmsswloglevel = 'ERROR'
                cmssw_base = '/home/dqmdevlocal'
                execdir = '/home/dqmdevlocal/output' ##not yet 

        #hardcode minidaq hosts until role is available
        #if cnhostname == 'bu-c2f13-27-01.cms' or cnhostname == 'fu-c2f13-19-03.cms' or cnhostname == 'fu-c2f13-19-04.cms':
        #    runindex_name = 'runindex_minidaq'
        #hardcode dqm hosts until role is available
        #if cnhostname == 'bu-c2f13-31-01.cms' or cnhostname == 'fu-c2f13-39-01.cms' or cnhostname == 'fu-c2f13-39-02.cms' or cnhostname == 'fu-c2f13-39-03.cms' or cnhostname == 'fu-c2f13-39-04.cms':
        #    runindex_name = 'runindex_dqm'
    else:
        runindex_name = 'test' 

    buName = ''
    budomain = ''
    if type == 'fu':
        if cluster == 'daq2val' or cluster == 'daq2': 
            addrList =  getBUAddr(cluster,cnhostname)
            selectedAddr = False
            for addr in addrList:
                #result = os.system("ping -c 1 "+ str(addr[1])+" >& /dev/null")
                result = 0#ping disabled for now
                #os.system("clear")
                if result == 0:
                    buDataAddr = addr[1]
                    if addr[1].find('.'):
                        buName = addr[1].split('.')[0]
                        budomain = addr[1][addr[1].find('.'):]
                    else:
                        buName = addr[1]
                    selectedAddr=True
                    break
                else:
                    print "failed to ping",str(addr[1])
            #if none are pingable, first one is picked
            if selectedAddr==False:
                if len(addrList)>0:
                    addr = addrList[0]
                    buDataAddr = addr[1]
                    if addr[1].find('.'):
                        buName = addr[1].split('.')[0]
                    else:
                        buName = addr[1]
            if buName == '':
                print "no BU found for this FU in the dabatase"
                sys.exit(-1)
 
        elif cluster =='test':
            hn = os.uname()[1].split(".")[0]
            addrList = [hn]
            buName = hn
            buDataAddr = hn
        else:
            print "FU configuration in cluster",cluster,"not supported yet !!"
            sys.exit(-2)

    elif type == 'bu':
        if env == "vm":
            buName = os.uname()[1].split(".")[0]
        else:
            buName = os.uname()[1]
        addrList = buName

    #print "detected address", addrList," and name ",buName
    print "running configuration for machine",cnhostname,"of type",type,"in cluster",cluster,"; appliance bu is:",buName

    clusterName='appliance_'+buName
    if 'elasticsearch' in selection:

        if env=="vm":
            es_publish_host=os.uname()[1]
        else:
            es_publish_host=os.uname()[1]+'.cms'

        #print "will modify sysconfig elasticsearch configuration"
        #maybe backup vanilla versions
        essysEdited =  checkModifiedConfigInFile(elasticsysconf)
        if essysEdited == False and type == 'fu': #modified only on FU
          #print "elasticsearch sysconfig configuration was not yet modified"
          shutil.copy(elasticsysconf,os.path.join(backup_dir,os.path.basename(elasticsysconf)))

        esEdited =  checkModifiedConfigInFile(elasticconf)
        if esEdited == False:
          shutil.copy(elasticconf,os.path.join(backup_dir,os.path.basename(elasticconf)))

        escfg = FileManager(elasticconf,':',esEdited,'',' ')

        escfg.reg('cluster.name',clusterName)
        escfg.reg('node.name',cnhostname)
        essyscfg = FileManager(elasticsysconf,'=',essysEdited)
        essyscfg.reg('ES_HEAP_SIZE','1G')
        essyscfg.commit()

        if type == 'fu':
            escfg.reg('discovery.zen.ping.multicast.enabled','false')
            if env=="vm":
                escfg.reg('discovery.zen.ping.unicast.hosts',"[\"" + buName + "\"]")
            else:
                escfg.reg('discovery.zen.ping.unicast.hosts',"[\"" + buName + ".cms" + "\"]")
            escfg.reg('network.publish_host',es_publish_host)
            escfg.reg('transport.tcp.compress','true')
            escfg.reg('indices.fielddata.cache.size', '50%')
            if cluster != 'test':
                escfg.reg('node.master','false')
                escfg.reg('node.data','true')
        if type == 'bu':
            escfg.reg('network.publish_host',es_publish_host)
            #escfg.reg('discovery.zen.ping.multicast.enabled','false')
            #escfg.reg('discovery.zen.ping.unicast.hosts','[ \"'+elastic_host2+'\" ]')
            escfg.reg('transport.tcp.compress','true')
            escfg.reg('node.master','true')
            escfg.reg('node.data','false')

        escfg.commit()

    if "hltd" in selection:

      #first prepare bus.config file
      if type == 'fu':
        try:
          shutil.copy(busconfig,os.path.join(backup_dir,os.path.basename(busconfig)))
          os.remove(busconfig)
        except Exception,ex:
          print "problem with copying bus.config? ",ex
          pass

      #write bu ip address
        print "WRITING BUS CONFIG ", busconfig
        f = open(busconfig,'w+')
        f.writelines(getIPs(buDataAddr)[0])
        f.close()

      #FU should have one instance assigned, BUs can have multiple
      watch_dir_bu = '/fff/ramdisk'
      out_dir_bu = '/fff/output'
      log_dir_bu = '/var/log/hltd'

      instances,sizes=getInstances(os.uname()[1])
      if len(instances)==0: instances=['main']

      hltdEdited = checkModifiedConfigInFile(hltdconf)
      #print "was modified?",hltdEdited
      if hltdEdited == False:
        shutil.copy(hltdconf,os.path.join(backup_dir,os.path.basename(hltdconf)))

      if type=='bu':

        try:os.remove('/etc/hltd.instances')
        except:pass
        #do major ramdisk cleanup (unmount existing loop mount points, run directories and img files)
        try:
            subprocess.check_call(['/opt/hltd/scripts/unmountloopfs.sh','/fff/ramdisk'])
            os.popen('rm -rf /fff/ramdisk/run*')
        except subprocess.CalledProcessError, err1:
            print 'failed to cleanup ramdisk',err1
        except Exception as ex:
            print 'failed to cleanup ramdisk',ex
 
        cgibase=9000
        for idx,val in enumerate(instances):
          if idx!=0 and val=='main':
            instances[idx]=instances[0]
            instances[0]=val
            break
        for idx, instance in enumerate(instances):

          watch_dir_bu = '/fff/ramdisk'
          out_dir_bu = '/fff/output'
          log_dir_bu = '/var/log/hltd'

          cfile = hltdconf
          if instance != 'main':
            cfile = '/etc/hltd-'+instance+'.conf'
            shutil.copy(hltdconf,cfile)
            watch_dir_bu = os.path.join(watch_dir_bu,instance)
            out_dir_bu = os.path.join(out_dir_bu,instance)
            log_dir_bu = os.path.join(log_dir_bu,instance)
            #run loopback setup for non-main instances
            try:
                subprocess.check_call(['/opt/hltd/scripts/makeloopfs.sh','/fff/ramdisk',instance, str(sizes[idx])])
            except subprocess.CalledProcessError, err1:
                print 'failed to configure loopback device mount in ramdisk'


          soap2file_port='0'
 
          if myhost in dqm_list or myhost in ed_list or cluster == 'daq2val':
              soap2file_port='8010'

          hltdcfg = FileManager(cfile,'=',hltdEdited,' ',' ')

          hltdcfg.reg('enabled','True','[General]')
      
          hltdcfg.reg('user',username,'[General]')
          hltdcfg.reg('instance',instance,'[General]')

          #port for multiple instances
          hltdcfg.reg('cgi_port',str(cgibase+idx),'[Web]')
          hltdcfg.reg('cgi_instance_port_offset',str(idx),'[Web]')
          hltdcfg.reg('soap2file_port',soap2file_port,'[Web]')

          hltdcfg.reg('elastic_cluster',clusterName,'[Monitoring]')
          hltdcfg.reg('watch_directory',watch_dir_bu,'[General]')
          hltdcfg.reg('role','bu','[General]')
          hltdcfg.reg('micromerge_output',out_dir_bu,'[General]')
          hltdcfg.reg('elastic_runindex_url',elastic_host,'[Monitoring]')
          hltdcfg.reg('elastic_runindex_name',runindex_name,'[Monitoring]')
          hltdcfg.reg('use_elasticsearch',use_elasticsearch,'[Monitoring]')
          hltdcfg.reg('es_cmssw_log_level',cmsswloglevel,'[Monitoring]')
          hltdcfg.reg('dqm_machine',dqmmachine,'[DQM]')
          hltdcfg.reg('log_dir',log_dir_bu,'[Logs]')
          hltdcfg.commit()

        #write all instances in a file
        if 'main' not in instances or len(instances)>1:
          with open('/etc/hltd.instances',"w") as fi:
            for instance in instances: fi.write(instance+"\n")


      if type=='fu':
          hltdcfg = FileManager(hltdconf,'=',hltdEdited,' ',' ')

          #FU can only have one instance (so we take instance[0] and ignore others)
          hltdcfg.reg('instance',instances[0],'[General]')

          hltdcfg.reg('exec_directory',execdir,'[General]') 
          hltdcfg.reg('user',username,'[General]')
          hltdcfg.reg('watch_directory','/fff/data','[General]')
          hltdcfg.reg('role','fu','[General]')
          hltdcfg.reg('cgi_port','9000','[Web]')
          hltdcfg.reg('cgi_instance_port_offset',"0",'[Web]')
          hltdcfg.reg('soap2file_port','0','[Web]')
          hltdcfg.reg('elastic_cluster',clusterName,'[Monitoring]')
          hltdcfg.reg('es_cmssw_log_level',cmsswloglevel,'[Monitoring]')
          hltdcfg.reg('elastic_runindex_url',elastic_host,'[Monitoring]')
          hltdcfg.reg('elastic_runindex_name',runindex_name,'[Monitoring]')
          hltdcfg.reg('use_elasticsearch',use_elasticsearch,'[Monitoring]')
          hltdcfg.reg('dqm_machine',dqmmachine,'[DQM]')
          hltdcfg.reg('cmssw_base',cmssw_base,'[CMSSW]')
          hltdcfg.reg('cmssw_default_version',cmssw_version,'[CMSSW]')
          hltdcfg.reg('cmssw_threads',nthreads,'[CMSSW]')
          hltdcfg.reg('cmssw_streams',nfwkstreams,'[CMSSW]')
          hltdcfg.reg('resource_use_fraction',resourcefract,'[Resources]')
          hltdcfg.commit()

