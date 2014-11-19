#/!bin/bash
if [ -n "$1" ]; then
  if [ -f $1 ]; then

    basedir=`readlink -e $1`
    umask 0
    mount | grep $basedir/ | grep /dev/loop | awk '{print $3}' | umount

    if [ $? != 0 ]; then
      echo "Unsuccessful umount of ${basedir}/"
      exit 2
    fi
    exit 0
  else
    echo "base directory not found!"
  fi
fi
exit 1

