#!/bin/bash
if [ -n "$1" ]; then
x=0
else
echo ""
echo "Usage: please provide path name for which to kill all processes keeping it busy."
echo ""
exit 1
fi
killpid=`lsof $1 | awk -v N=$2 '{print $2}' | grep -v PID`
if [[ $killpid != "" ]]; then
echo "$1 is being used by: $killpid. Trying to kill these processes."
myarr=($killpid)
for i in "${myarr[@]}"
do
    kill -9 $i
done
sleep 1
echo ""

else
echo "No offenders found."
echo ""
fi
