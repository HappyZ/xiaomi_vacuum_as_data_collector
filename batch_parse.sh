#!/bin/bash

LOG_FILE=batch_parse.log
PYTHON=python
VERSION=$(${PYTHON} -c 'import platform; major, minor, patch = platform.python_version_tuple(); print(major);')

if [ VERSION == 2 ]; then
    PYTHON=python3
    VERSION=$(${PYTHON} -c 'import platform; major, minor, patch = platform.python_version_tuple(); print(major);')
fi

if [ VERSION == 3 ]; then
    echo "cannot find the right python version 3"
    exit
fi

echo "python to be used: ${PYTHON} at $(which ${PYTHON})"

if [ "$#" -lt 2 ]; then
    echo "usage: $0 <folder-to-be-parsed> <output-folder-path-suffix> <optional: sampling num>"
    exit
fi

if [ ! -d "$1" ]; then
    echo "cannot find directory: '${1}'"
    exit
fi

SAMPLING_NUM=50
if [ "$#" -eq 3 ]; then
    SAMPLING_NUM=$3
fi

echo "working on folder '$1'"

mkdir -p ${2}_all
mkdir -p ${2}_horiz
mkdir -p ${2}_verti
mkdir -p ${2}_subsampled
mkdir -p ${2}_direction_0
mkdir -p ${2}_direction_1
mkdir -p ${2}_direction_2
mkdir -p ${2}_direction_3

for folder in ${1%/}/*; do
    if [ ! -d "$folder" ]; then
        continue
    fi
    # prepare
    ORIENT=$(echo ${folder} | awk -F "_" '{print $NF}')
    if [ $ORIENT = "0" ]; then
        MOVE_TO_FOLDER=${2}_horiz
    elif [ $ORIENT = "2" ]; then
        MOVE_TO_FOLDER=${2}_horiz
    elif [ $ORIENT = "1" ]; then
        MOVE_TO_FOLDER=${2}_verti
    elif [ $ORIENT = "3" ]; then
        MOVE_TO_FOLDER=${2}_verti
    else
        continue
    fi

    echo "processing folder: ${folder}.." >> $LOG_FILE 2>&1

    echo "########################################"
    echo "     processing folder: ${folder}.."
    echo "########################################"

    ${PYTHON} preprocessor.py "${folder}" --pickle -vd >> $LOG_FILE 2>&1
    if [ ! $? -eq 0 ]; then
        echo "missing required files.."
        continue
    fi
    echo "########################################"
    echo "     default"
    echo "########################################"
    for file in $(find ${folder} -name "*.png" -o -name "*.pickle"); do
        cp ${file} ${2}_all/
        mv ${file} $MOVE_TO_FOLDER/
    done

    echo "########################################"
    echo "     subsampling"
    echo "########################################"
    # ${PYTHON} preprocessor.py "${folder}" --pickle -vd --sampling --sampling-num ${SAMPLING_NUM} > $LOG_FILE 2>&1
    # for file in $(find ${folder} -name "*.png" -o -name "*.pickle"); do
    #     mv ${file} ${2}_subsampled/
    # done

    echo "########################################"
    echo "     extract based on moving direction"
    echo "########################################"
    if [ $MOVE_TO_FOLDER = "${2}_horiz" ]; then
        ${PYTHON} preprocessor.py "${folder}" --pickle -vd --filters 0 >> $LOG_FILE 2>&1
        for file in $(find ${folder} -name "*.png" -o -name "*.pickle"); do
            mv ${file} ${2}_direction_0/
        done
        ${PYTHON} preprocessor.py "${folder}" --pickle -vd --filters 2 >> $LOG_FILE 2>&1
        for file in $(find ${folder} -name "*.png" -o -name "*.pickle"); do
            mv ${file} ${2}_direction_2/
        done
    elif [ $MOVE_TO_FOLDER = "${2}_verti" ]; then
        ${PYTHON} preprocessor.py "${folder}" --pickle -vd --filters 1 >> $LOG_FILE 2>&1
        for file in $(find ${folder} -name "*.png" -o -name "*.pickle"); do
            mv ${file} ${2}_direction_1/
        done
        ${PYTHON} preprocessor.py "${folder}" --pickle -vd --filters 3 >> $LOG_FILE 2>&1
        for file in $(find ${folder} -name "*.png" -o -name "*.pickle"); do
            mv ${file} ${2}_direction_3/
        done
    fi
done
#     python3 ../xiaomi_vacuum_as_data_collector/preprocessor.py "$1/$i" --map