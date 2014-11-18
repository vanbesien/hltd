#/!bin/bash
if [ -n "$1" ]; then
  if [ -n "$2" ]; then
    if [ -n "$3" ]; then


      if [ -f $1 ]; then
        echo "base directory not found!"
      fi

      basedir=`readlink -e $1`
      image=$basedir/$2.img
      mountpoint=$basedir/$2
      sizemb=$3
      ret=0
      umask 0

      echo "makeloop script invoked for creating loop device disk $2 in ${basedir} of size $3 MB"

      #mount | grep "$mountpoint" | while read a; do ret=umount  $mountpoint; done
      umount  $mountpoint

      if [ $? != 0 ]; then
        echo "Unsuccessful umount of ${mountpoint}"

        
        killpid=`lsof /dev/shm/myruns/img2 | awk -v N=$2 '{print $2}' | grep -v PID`
        #killpid=`lsof /dev/shm/myruns/img2  | grep -v COMMAND | awk -v N=$2 '{print $2}'`
        echo "used by: $killpid. Trying to kill these processes."
        myarr=($killpid)
        for i in "${myarr[@]}"
        do
            if [ $i == $$ ]; then
            exit 9
            fi
            kill -9 $i
        done
        sleep 1
        umount  $mountpoint
        if [ $? != 0 ]; then
          echo "Unsuccessful umount of ${mountpoint}. Still busy."
          exit 2
        fi

      fi
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

