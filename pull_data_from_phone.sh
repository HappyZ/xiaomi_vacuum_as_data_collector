#!/bin/bash

PHONEPATH=$1
LOCALFOLDER=$2

mkdir -p $LOCALFOLDER

if [[ ! $? -eq 0 ]]; then
    echo "Cannot create folder $LOCALFOLDER"
    exit $?;
fi


for file in $(adb shell "ls $PHONEPATH" | tr -d '\r'); do
    if [[ $PHONEPATH = *"*" ]]; then
        adb pull "${PHONEPATH%%/*}/$file" $LOCALFOLDER/
        if [[ $? -eq 0 ]]; then
            adb shell rm "${PHONEPATH%%/*}/$file"
        fi
    else
        adb pull "$PHONEPATH/$file" $LOCALFOLDER/
        if [[ $? -eq 0 ]]; then
            adb shell rm "$PHONEPATH/$file"
        fi
    fi
done
