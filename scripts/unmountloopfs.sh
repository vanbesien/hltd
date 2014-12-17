#!/bin/bash
if [ -n "$1" ]; then
  if [ -d $1 ]; then

    basedir=`readlink -e $1`
    umask 0
    points=`mount | grep $basedir/ | grep /dev/loop | awk '{print $3}'`
    imgs=`mount | grep $basedir/ | grep /dev/loop | awk '{print $1}'`
    pointarr=( $points )
    imgarr=( $imgs )

    len=${#pointarr[@]}
    len2=${#imgarr[@]}
    if [[ $len == 0 ]]; then
      echo "no loopback mount points present."
      exit 0
    fi
    max=$((len-1))

    for i in {0..$max}
    do
      point=${pointarr[$i]}
      image=${imgarr[$i]}
      #protect from dangerous action
      if [ $point == "/" ]; then continue; fi
      if [ $point == "//" ]; then continue; fi
      if [ $point == "/fff" ]; then continue; fi
      if [ $point == "/fff/" ]; then continue; fi
      if [ $point == "/fff/ramdisk" ]; then continue; fi
      if [ $point == "/fff/ramdisk/" ]; then continue; fi
      if [ $point == "fff/ramdisk" ]; then continue; fi
      if [ $point == "fff/ramdisk/" ]; then continue; fi

      echo "found mountpoint $point $image"

      #prevent FUs from writing boxinfo files by moving directory away
      mv $point/appliance $point/appliance-delete
      sleep 1

      #unmunt loop device
      unmount $point
      if [ $? != 0 ]; then
        echo "Trying to kill processes which use mountpoint $point"
        killpid=`lsof $point | awk -v N=$dummy '{print $2}' | grep -v PID`
        if [[ $killpid != "" ]]; then
          echo "$1 is being used by: $killpid. Trying to kill these processes."
          myarr=($killpid)
          for i in "${myarr[@]}"
          do
            kill -9 $i
          done
        else
          echo "No offenders found."
        fi
        sleep 1
        unmount $point
        if [ $? != 0 ]; then
          echo "Unsuccessful umount of $point"
          exit 2
        fi
      fi

      #deleting mount point
      rm -rf $point
      if [ $? != 0 ]; then
        echo "Unsuccessful delete of unmounted mount point $point !"
        exit 3
      fi

      #remove image
      chmod 755 $image
      rm -rf $image
      if [ $? != 0 ]; then
        echo "Unsuccessful delete of image file $image"
        exit 4
      fi
    echo "Successfully cleaned up mount point $point and deleted image file $image."
    done
    exit 0
  else
    echo "base directory not found!"
  fi
fi
exit 1
