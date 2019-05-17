#!/usr/bin/python

import os
import sys
import argparse

from libs.parser_post import build_map
from libs.parser_post import translate_pcap
from libs.parser_post import combine_sig_loc
from libs.parser_post import convert_to_pickle_rss
from libs.parser_post import get_locs_from_slam_data
from libs.parser_post import get_locs_from_parsed_sig_data
from libs.parser_post import extract_dev_from_combined


def get_files(folder):
    files = os.listdir(folder)
    f_map_image = None
    f_loc_est = None
    f_sig_data = None
    is_csi = False
    for file in files:
        if '.pcap' in file:
            f_sig_data = "{0}/{1}".format(folder, file)
            if "csi" in file:
                is_csi = True
        elif 'loc.csv' in file:
            f_loc_est = "{0}/{1}".format(folder, file)
        elif 'map.ppm' in file:
            f_map_image = "{0}/{1}".format(folder, file)
    return f_map_image, f_loc_est, f_sig_data, is_csi


def generate_floorplan_map(f_map, f_loc, f_sig_extracted, is_csi):
    '''
    generate maps for path and signals
    '''

    # get map image
    with open(f_map, 'rb') as f:
        map_image_data = f.read()

    # build a general map without signal
    with open(f_loc) as f:
        # skip the first line which is coumn names
        slam_data = f.readlines()[1:]
    augmented_map = build_map(
        get_locs_from_slam_data(slam_data),
        map_image_data
    )
    filepath, ext = os.path.splitext(f_map)
    with open("{}.png".format(filepath), 'wb') as f:
        f.write(augmented_map.getvalue())

    for f_each in f_sig_extracted:
        with open(f_each) as f:
            # skip the first line which is coumn names
            parsed_sig_data = f.readlines()[1:]
        augmented_map = build_map(
            get_locs_from_parsed_sig_data(parsed_sig_data, is_csi),
            map_image_data
        )
        filepath, ext = os.path.splitext(f_each)
        with open("{}.png".format(filepath), 'wb') as f:
            f.write(augmented_map.getvalue())


def convert_to_pickle(filepaths, orientation, visualize, is_csi):
    '''
    '''
    if is_csi:
        print("Err: not implemented for CSIs yet")
        return
    for filepath in filepaths:
        print("parsing file: {}".format(filepath))
        try:
            convert_to_pickle_rss(filepath, orientation, visualize)
        except KeyboardInterrupt:
            print("KeyboardInterrupt happened")


def main(args):
    if not os.path.isdir(args.folder):
        print("Err: folder {} does not exist".format(args.folder))
        sys.exit(2)
    f_map, f_loc, f_sig, is_csi = get_files(args.folder)
    if f_loc is None or f_sig is None:
        print("Err: desired files not exist")
        sys.exit(2)

    # parse pcap into csv, and add location if it has one
    f_sig_parsed = translate_pcap(f_sig, is_csi)
    f_sig_combined = combine_sig_loc(f_sig_parsed, f_loc)
    f_sig_extracted = extract_dev_from_combined(f_sig_combined, minimalCounts=5000)

    if args.pickle:
        convert_to_pickle(f_sig_extracted, args.orientation, args.visualize, is_csi)

    # generate path in map for visualization
    if args.map:
        generate_floorplan_map(f_map, f_loc, f_sig_extracted, is_csi)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Data Pre-Processor'
    )
    parser.add_argument(
        dest='folder',
        help='Specify folder path of data'
    )
    parser.add_argument(
        '--map',
        dest='map',
        action='store_true',
        default=False,
        help='Enable to generate map images with scanned floorplan'
    )
    parser.add_argument(
        '--pickle',
        dest='pickle',
        action='store_true',
        default=False,
        help='Enable to dump into pickle images'
    )
    parser.add_argument(
        '--visualize', '-v',
        dest='visualize',
        action='store_true',
        default=False,
        help='Enable to visualize map images while dumping to pickles'
    )
    parser.add_argument(
        '--orient',
        dest='orientation',
        type=int,
        default=0,
        help='Specify orientation of the map'
    )
    args = parser.parse_known_args()

    main(args)