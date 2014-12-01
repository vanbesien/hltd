#!/bin/bash
if [ -n "$1" ]; then
  if [ -d $1 ]; then

    basedir=`readlink -e $1`
    umask 0
    var=`mount | grep $basedir/ | grep /dev/loop | awk '{print $3}'`
    imgs=`mount | grep $basedir/ | grep /dev/loop | awk '{print $1}'`
    vararr=( $var )
    imgarr=( $imgs )
    #echo ${tokens[2]}
    printf %s "$var" | while IFS= read -r line
    do
      unmount $line
      if [ $? != 0 ]; then
        echo "Unsuccessful umount of ${basedir}/"
        exit 2
      fi
      image="${line}.img"
      chmod 755 $img
      rm -rf $image
      if [ $? != 0 ]; then
        echo "Unsuccessful delete old image file $image"
        exit 3
      fi
      rm -rf $mountpoint
      if [ $? != 0 ]; then
        echo "Unsuccessful delete old mount point dir!"
        exit 4
      fi
    done
    exit 0
  else
    echo "base directory not found!"
  fi
fi
exit 1
