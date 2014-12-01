#!/bin/bash -e
BUILD_ARCH=noarch
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPTDIR/..
BASEDIR=$PWD

PACKAGENAME="fffmeta"

PARAMCACHE="paramcache"

if [ -n "$1" ]; then
  PARAMCACHE=$1
fi

if [ -n "$2" ]; then
  PACKAGENAME=$2
fi

echo "Using cache file $PARAMCACHE"

if [ -f $SCRIPTDIR/$PARAMCACHE ];
then
  readarray lines < $SCRIPTDIR/$PARAMCACHE
  for (( i=0; i < 12; i++ ))
  do
    lines[$i]=`echo -n ${lines[$i]} | tr -d "\n"`
  done
else
  for (( i=0; i < 12; i++ ))
  do
    lines[$i]=""
  done
fi





echo "Enviroment (prod,vm) (press enter for \"${lines[0]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[0]=$readin
fi

echo "ES server URL containg common run index (press enter for \"${lines[1]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[1]=$readin
fi

echo "CMSSW base (press enter for \"${lines[2]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[2]=$readin
fi

echo "HWCFG DB server (press enter for \"${lines[3]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[3]=$readin
fi

echo "HWCFG DB SID (or db name in VM enviroment) (press enter for: \"${lines[4]}\"):"
echo "(SPECIFIES address in TNSNAMES.ORA file if DB server field was \"null\"!)"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[4]=$readin
fi

echo "HWCFG DB username (press enter for: \"${lines[5]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[5]=$readin
fi

echo "HWCFG DB password (press enter for: \"${lines[6]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[6]=$readin
fi

echo "Equipment set (press enter for: \"${lines[7]}\") - type 'latest' or enter a specific one:"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[7]=$readin
fi

echo "job username (press enter for: \"${lines[8]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[8]=$readin
fi

echo "number of threads per process (press enter for: ${lines[9]}):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[9]=$readin
fi


echo "number of framework streams per process (press enter for: ${lines[10]}):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[10]=$readin
fi



echo "CMSSW log collection level (DEBUG,INFO,WARNING,ERROR or FATAL) (press enter for: ${lines[11]}):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[11]=$readin
fi



params=""
for (( i=0; i < 12; i++ ))
do
  params="$params ${lines[i]}"
done

#write cache
if [ -f $SCRIPTDIR/$PARAMCACHE ];
then
rm -rf -f $SCRIPTDIR/$PARAMCACHE
fi
for (( i=0; i < 12; i++ ))
do
  echo ${lines[$i]} >> $SCRIPTDIR/$PARAMCACHE
done

chmod 500 $SCRIPTDIR/$PARAMCACHE
# create a build area

echo "removing old build area"
rm -rf /tmp/fffmeta-build-tmp
echo "creating new build area"
mkdir  /tmp/fffmeta-build-tmp
ls
cd     /tmp/fffmeta-build-tmp
mkdir BUILD
mkdir RPMS
TOPDIR=$PWD
echo "working in $PWD"
ls

pluginpath="/opt/fff/esplugins/"
pluginname1="bigdesk"
pluginfile1="lukas-vlcek-bigdesk-v2.4.0-2-g9807b92-mod.zip"

cd $TOPDIR
# we are done here, write the specs and make the fu***** rpm
cat > fffmeta.spec <<EOF
Name: $PACKAGENAME
Version: 1.5.3
Release: 4
Summary: hlt daemon
License: gpl
Group: DAQ
Packager: smorovic
Source: none
%define _topdir $TOPDIR
BuildArch: $BUILD_ARCH
AutoReqProv: no
Requires:elasticsearch >= 1.2.0, hltd >= 1.5.3, cx_Oracle >= 5.1.2, java-1.7.0-openjdk

Provides:/opt/fff/configurefff.sh
Provides:/opt/fff/setupmachine.py
Provides:/opt/fff/instances.input
Provides:/etc/init.d/fffmeta

#Provides:/opt/fff/backup/elasticsearch.yml
#Provides:/opt/fff/backup/elasticsearch
#Provides:/opt/fff/backup/hltd.conf

%description
fffmeta configuration setup package

%prep
%build

%install
rm -rf \$RPM_BUILD_ROOT
mkdir -p \$RPM_BUILD_ROOT
%__install -d "%{buildroot}/opt/fff"
%__install -d "%{buildroot}/opt/fff/backup"
%__install -d "%{buildroot}/opt/fff/esplugins"
%__install -d "%{buildroot}/etc/init.d"

mkdir -p opt/fff/esplugins
mkdir -p opt/fff/backup
mkdir -p etc/init.d/
cp $BASEDIR/python/setupmachine.py %{buildroot}/opt/fff/setupmachine.py
cp $BASEDIR/etc/instances.input %{buildroot}/opt/fff/instances.input
echo "#!/bin/bash" > %{buildroot}/opt/fff/configurefff.sh
echo python2.6 /opt/fff/setupmachine.py elasticsearch,hltd $params >> %{buildroot}/opt/fff/configurefff.sh 

cp $BASEDIR/esplugins/$pluginfile1 %{buildroot}/opt/fff/esplugins/$pluginfile1
cp $BASEDIR/esplugins/install.sh %{buildroot}/opt/fff/esplugins/install.sh
cp $BASEDIR/esplugins/uninstall.sh %{buildroot}/opt/fff/esplugins/uninstall.sh

echo "#!/bin/bash"                       >> %{buildroot}/etc/init.d/fffmeta
echo "#"                                 >> %{buildroot}/etc/init.d/fffmeta
echo "# chkconfig:   2345 79 22"         >> %{buildroot}/etc/init.d/fffmeta
echo "#"                                 >> %{buildroot}/etc/init.d/fffmeta
echo "if [ \\\$1 == \"start\" ]; then"   >> %{buildroot}/etc/init.d/fffmeta
echo "  /opt/fff/configurefff.sh"  >> %{buildroot}/etc/init.d/fffmeta
echo "  exit 0"                          >> %{buildroot}/etc/init.d/fffmeta
echo "fi"                                >> %{buildroot}/etc/init.d/fffmeta
echo "if [ \\\$1 == \"restart\" ]; then" >> %{buildroot}/etc/init.d/fffmeta
echo "/opt/fff/configurefff.sh"    >> %{buildroot}/etc/init.d/fffmeta
echo "  exit 0"                          >> %{buildroot}/etc/init.d/fffmeta
echo "fi"                                >> %{buildroot}/etc/init.d/fffmeta
echo "if [ \\\$1 == \"status\" ]; then"  >> %{buildroot}/etc/init.d/fffmeta
echo "echo fffmeta does not have status" >> %{buildroot}/etc/init.d/fffmeta
echo "  exit 0"                          >> %{buildroot}/etc/init.d/fffmeta
echo "fi"                                >> %{buildroot}/etc/init.d/fffmeta


%files
%defattr(-, root, root, -)
#/opt/fff
%attr( 755 ,root, root) /opt/fff/setupmachine.py
%attr( 755 ,root, root) /opt/fff/setupmachine.pyc
%attr( 755 ,root, root) /opt/fff/setupmachine.pyo
%attr( 755 ,root, root) /opt/fff/instances.input
%attr( 700 ,root, root) /opt/fff/configurefff.sh
%attr( 755 ,root, root) /etc/init.d/fffmeta
%attr( 444 ,root, root) /opt/fff/esplugins/$pluginfile1
%attr( 755 ,root, root) /opt/fff/esplugins/install.sh
%attr( 755 ,root, root) /opt/fff/esplugins/uninstall.sh

%post
#echo "post install trigger"
chkconfig --del fffmeta
chkconfig --add fffmeta
#disabled, can be run manually for now

%triggerin -- elasticsearch
#echo "triggered on elasticsearch update or install"
/sbin/service elasticsearch stop
python2.6 /opt/fff/setupmachine.py restore,elasticsearch
python2.6 /opt/fff/setupmachine.py elasticsearch $params
#update permissions in case new rpm changed uid/guid
chown -R elasticsearch:elasticsearch /var/log/elasticsearch
chown -R elasticsearch:elasticsearch /var/lib/elasticsearch
echo /opt/fff/esplugins/uninstall.sh /usr/share/elasticsearch $pluginname1
/opt/fff/esplugins/uninstall.sh /usr/share/elasticsearch $pluginname1
echo /opt/fff/esplugins/install.sh /usr/share/elasticsearch $pluginfile1 $pluginname1
/opt/fff/esplugins/install.sh /usr/share/elasticsearch $pluginfile1 $pluginname1
/sbin/service elasticsearch start
chkconfig --del elasticsearch
chkconfig --add elasticsearch

#taskset elasticsearch process
#sleep 1
#ESPID=`cat /var/run/elasticsearch/elasticsearch.pid` || (echo "could not find elasticsearch pid";ESPID=0)
#if[ \$ESPID !="0" ]; then
#taskset -pc 3,4 \$ESPID
#fi

%triggerin -- hltd
#echo "triggered on hltd update or install"
if [ -f /etc/hltd.instances ]; then
/sbin/service hltd stop all
else
/sbin/service hltd stop || true
fi
rm -rf /etc/hltd.instances
python2.6 /opt/fff/setupmachine.py restore,hltd
python2.6 /opt/fff/setupmachine.py hltd $params

#adjust ownership of unpriviledged child process log files

if [ -f /var/log/hltd/elastic.log ]; then
chown ${lines[8]} /var/log/hltd/elastic.log
fi

if [ -f /var/log/hltd/anelastic.log ]; then
chown ${lines[8]} /var/log/hltd/anelastic.log
fi

#set up resources for hltd
/opt/hltd/python/fillresources.py

if [ -f /etc/hltd.instances ]; then
  /sbin/service hltd restart all
else
  /sbin/service hltd restart
fi

chkconfig --del hltd
#chkconfig --del soap2file
chkconfig --add hltd
#chkconfig --add soap2file
%preun

if [ \$1 == 0 ]; then 

  chkconfig --del fffmeta
  chkconfig --del elasticsearch
  chkconfig --del hltd
#  chkconfig --del soap2file

  /sbin/service elasticsearch stop || true
  /opt/fff/esplugins/uninstall.sh /usr/share/elasticsearch $pluginname1 || true

  if [ -f /etc/hltd.instances ]; then
    /sbin/service hltd stop all || true
  else
    /sbin/service hltd stop || true
  fi

  python2.6 /opt/fff/setupmachine.py restore,hltd,elasticsearch
fi

#TODO:
#%verifyscript

EOF

rpmbuild --target noarch --define "_topdir `pwd`/RPMBUILD" -bb fffmeta.spec

