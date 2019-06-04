#!/bin/bash

REMOTE="root@${MIROBO_IP}"
EXP_FP="/mnt/data/exp"
REMOTE_EXP_FP="${REMOTE}:${EXP_FP}"
REMOTE_CMD="ssh -t ${REMOTE}"


echo "IP: ${MIROBO_IP}"
echo "EXP_FP: ${EXP_FP}"

echo "Create folder on vacuum.."
${REMOTE_CMD} mkdir -p ${EXP_FP}/libs

echo "Push files to vacuum to run.."
scp ./libs/__init__.py ${REMOTE_EXP_FP}/libs/
scp ./libs/parser.py ${REMOTE_EXP_FP}/libs/
scp ./get_loc_est.py ${REMOTE_EXP_FP}

echo "Install necessary packages"
${REMOTE_CMD} apt update
${REMOTE_CMD} apt --yes install python3-minimal

echo "Done!"
