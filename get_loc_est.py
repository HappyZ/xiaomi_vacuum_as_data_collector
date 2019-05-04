import argparse
import subprocess

from libs.parser import get_slam_log


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
