import argparse
import subprocess

from libs.parser import get_slam_log


# This script supposes to run ON THE VACUUM
# do not run it on your local pc


# args
parser = argparse.ArgumentParser(
    description='Get Location Estimation from SLAM log on the vacuum'
)
parser.add_argument(
    dest='filepath',
    help='Specify output file path'
)
args, __ = parser.parse_known_args()

# fetch slam
get_slam_log(outputfile=args.filepath)
