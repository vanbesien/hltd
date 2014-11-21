#!/bin/bash
if [ -n "$1" ]; then
  if [ -d $1 ]; then

    basedir=`readlink -e $1`
    umask 0
    var=`mount | grep $basedir/ | grep /dev/loop | awk '{print $3}'`
    printf %s "$var" | while IFS= read -r line
    do
       unmount $line
    done
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

