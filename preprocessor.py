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
from libs.parser_post import get_groundtruth_dict


def get_files(folder):
    files = os.listdir(folder)
    f_map_image = None
    f_loc_est = None
    f_sig_data = None
    f_groundtruth = None
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
        elif 'gt.txt' in file:
            f_groundtruth = "{0}/{1}".format(folder, file)
    return f_map_image, f_loc_est, f_sig_data, f_groundtruth, is_csi


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


def convert_to_pickle(
    filepaths, 
    orientation,
    groundtruth=None,
    filters=None,
    visualize=False, 
    is_csi=False,
    output_map=False,
    sampling=False, 
    sampling_num=5
):
    '''
    '''
    if is_csi:
        print("Err: not implemented for CSIs yet")
        return
    for filepath in filepaths:
        print("parsing file: {}".format(filepath))
        if not sampling:
            sampling_num = 1
        for __ in range(sampling_num):
            try:
                if filters is 6:
                    for fff in range(0, 6):
                        convert_to_pickle_rss(
                            filepath, orientation,
                            labels=groundtruth.get(os.path.splitext(os.path.basename(filepath))[0], None),
                            visualize=visualize,
                            output_map=output_map,
                            filters=fff,
                            sampling=sampling
                        )
                else:
                    convert_to_pickle_rss(
                        filepath, orientation,
                        labels=groundtruth.get(os.path.splitext(os.path.basename(filepath))[0], None),
                        visualize=visualize,
                        output_map=output_map,
                        filters=filters,
                        sampling=sampling
                    )
            except KeyboardInterrupt:
                print("KeyboardInterrupt happened")
                return


def main(args):
    if not os.path.isdir(args.folder):
        print("Err: folder {} does not exist".format(args.folder))
        sys.exit(2)
    if 'orient' in args.folder:
        orientation = int(args.folder.rstrip('/').split('_')[-1])
        print("orientation: {}".format(orientation))
    f_map, f_loc, f_sig, f_gt, is_csi = get_files(args.folder)
    if f_loc is None or f_sig is None:
        print("Err: desired files not exist")
        sys.exit(2)

    # parse pcap into csv, and add location if it has one
    f_sig_parsed = translate_pcap(f_sig, is_csi)
    f_sig_combined = combine_sig_loc(f_sig_parsed, f_loc)
    f_sig_extracted = extract_dev_from_combined(f_sig_combined, minimalCounts=5000)

    gts = get_groundtruth_dict(f_gt)

    if args.pickle:
        # f_sig_extracted = [x for x in f_sig_extracted if '98fc11691fc5' in x]
        convert_to_pickle(
            f_sig_extracted,
            args.orientation,
            groundtruth=gts,
            filters=args.filters,
            visualize=args.visualize,
            is_csi=is_csi,
            output_map=args.visualize_dump,
            sampling=args.sampling,
            sampling_num=args.sampling_num
        )

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
        '--filters',
        dest='filters',
        type=int,
        default=None,
        help='Ignore the arg by default, set to x to extract only y `0: >`, `1: v`, `2: <`, `3: ^`, `4: <^>`, `5: <v>`, `6: all`'
    )
    parser.add_argument(
        '--sampling',
        dest='sampling',
        action='store_true',
        default=False,
        help='Enable subsampling to generate more data'
    )
    parser.add_argument(
        '--sampling-num',
        dest='sampling_num',
        type=int,
        default=10,
        help='If subsampling enabled, set the number of random samples performed'
    )
    parser.add_argument(
        '--visualize', '-v',
        dest='visualize',
        action='store_true',
        default=False,
        help='Enable to visualize map images while dumping to pickles'
    )
    parser.add_argument(
        '--visualize-dump', '-vd',
        dest='visualize_dump',
        action='store_true',
        default=False,
        help='Enable to dump images while dumping to pickles'
    )
    parser.add_argument(
        '--orient',
        dest='orientation',
        type=int,
        default=0,
        help='Specify orientation of the map'
    )
    args, __ = parser.parse_known_args()

    main(args)
