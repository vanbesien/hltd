#!/bin/bash
if [ -n "$1" ]; then
  if [ -n "$2" ]; then
    if [ -n "$3" ]; then

      if [ -d $1 ]; then

        basedir=`readlink -e $1`
        image=$basedir/$2.img
        mountpoint=$basedir/$2
        sizemb=$3
        ret=0
        umask 0

        #some protection against removing 
        if [ mountpoint == "/" ]; then exit 99; fi
        if [ mountpoint == "//" ]; then exit 99; fi
        if [ mountpoint == "/fff" ]; then exit 99; fi
        if [ mountpoint == "/fff/ramdisk" ]; then exit 99; fi 
        if [ mountpoint == "fff/ramdisk" ]; then exit 99; fi 

        echo "makeloop script invoked for creating loop device disk $2 in ${basedir} of size $3 MB"

        if [ -d $mountpoint ]; then

          var=`mount | grep $mountpoint | grep /dev/loop | awk '{print $3}'`
          echo "calling unmount $line"

          umount $var

          if [ $? != 0 ]; then
            echo "Unsuccessful umount of ${mountpoint}"

            killpid=`lsof $mountpoint | awk -v N=$2 '{print $2}' | grep -v PID`
            myarr=($killpid)
            for i in "${myarr[@]}"
            do
              echo "used by: $i. Trying to kill this process."
              kill -9 $i
            done
            sleep 1
            umount  $mountpoint
            if [ $? != 0 ]; then
              echo "Unsuccessful umount of ${mountpoint}. Still busy."
              exit 2
            fi
          fi
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
        fi
    
        chmod 555 $image
        dd if=/dev/zero of=$image bs=1048576 count=$sizemb >& /dev/null
        echo y | mkfs.ext3 $image > /dev/null
        #try mount
        mkdir $mountpoint

        if [ $? != 0 ]; then
          echo "Unsuccessful make mount point directory!"
          exit 4
        fi
 
        echo "mounting image directory..."
        exec mount -o loop $image $mountpoint

        if [ $? != 0 ]; then
          echo "Unsuccessful mount with parameters $image $mountpoint"
          exit 5
        fi
        return 0
      else
        echo "base directory not found!"
      fi
    else
      echo "No parameter 3 given!"
    fi
  else
    echo "No parameter 2 given!"
  fi
else
  echo "No parameter 1 given!"
fi
echo "Usage: makeloopfs.sh basedir subdir imgsize(MB)"
exit 1

