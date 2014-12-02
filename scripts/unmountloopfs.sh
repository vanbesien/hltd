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

      #protect from going wrong
      if [ $line == "/" ]; then continue; fi
      if [ $line == "//" ]; then continue; fi
      if [ $line == "/fff" ]; then continue; fi
      if [ $line == "/fff/" ]; then continue; fi
      if [ $line == "/fff/ramdisk" ]; then continue; fi
      if [ $line == "/fff/ramdisk/" ]; then continue; fi
      if [ $line == "fff/ramdisk" ]; then continue; fi
      if [ $line == "fff/ramdisk/" ]; then continue; fi

      #prevent FUs from writing boxinfo files by moving directory away
      mv $line/appliance $line/appliance-delete
      if [ $? != 0 ]; then
          sleep 0
      else
          sleep 1
      fi
      unmount $line
      if [ $? != 0 ]; then
        echo "Unsuccessful umount of ${basedir}/"
        exit 2
      fi
      image="${line}.img"
      chmod 755 $image
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
