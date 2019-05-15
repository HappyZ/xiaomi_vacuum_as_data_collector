#!/bin/bash

PHONEPATH=$1
LOCALFOLDER=$2

mkdir -p $LOCALFOLDER

for file in $(adb shell "ls $PHONEPATH" | tr -d '\r'); do
    if [[ $PHONEPATH = *"*" ]]; then
        adb pull "${PHONEPATH%%/*}/$file" $LOCALFOLDER/
        adb shell rm "${PHONEPATH%%/*}/$file"
    else
        adb pull "$PHONEPATH/$file" $LOCALFOLDER/
        adb shell rm "$PHONEPATH/$file"
    fi
done
