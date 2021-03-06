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


def convert_to_pickle(
    filepaths, 
    orientation,
    groundtruth=None,
    filters=None,
    visualize=False, 
    is_csi=False,
    output_map=False,
    sampling=False, 
    sampling_num=5,
    map_dim=None,
    map_res=0.1
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
                            sampling=sampling,
                            map_dim=map_dim,
                            map_res=map_res
                        )
                else:
                    convert_to_pickle_rss(
                        filepath, orientation,
                        labels=groundtruth.get(os.path.splitext(os.path.basename(filepath))[0], None),
                        visualize=visualize,
                        output_map=output_map,
                        filters=filters,
                        sampling=sampling,
                        map_dim=map_dim,
                        map_res=map_res
                    )
            except KeyboardInterrupt:
                print("KeyboardInterrupt happened")
                return


def main(args):
    if not os.path.isdir(args.folder):
        print("Err: folder {} does not exist".format(args.folder))
        sys.exit(2)
    if 'orient' in args.folder:
        args.orientation = int(args.folder.rstrip('/').split('_')[-1])
        print("args.orientation: {}".format(args.orientation))
    f_map, f_loc, f_sig, f_gt, is_csi = get_files(args.folder)
    if f_loc is None or f_sig is None:
        print("Err: desired files not exist")
        sys.exit(2)

    # parse pcap into csv, and add location if it has one
    f_sig_parsed = translate_pcap(f_sig, is_csi)
    f_sig_combined, minmax_xys = combine_sig_loc(f_sig_parsed, f_loc)
    f_sig_extracted = extract_dev_from_combined(f_sig_combined, minimalCounts=5000)

    gts = get_groundtruth_dict(f_gt)

    if args.pickle:
        convert_to_pickle(
            f_sig_extracted,
            args.orientation,
            groundtruth=gts,
            filters=args.filters,
            visualize=args.visualize,
            is_csi=is_csi,
            output_map=args.visualize_dump,
            sampling=args.sampling,
            sampling_num=args.sampling_num,
            map_dim=args.dimension,
            map_res=args.resolution
        )

    # generate path in map for visualization
    if args.map:
        build_map(
            f_map,
            args.orientation,
            minmax_xys,
            markers=gts,
            visualize=args.visualize,
            output_map=args.visualize_dump,
            map_dim=args.dimension,
            map_res=args.resolution
        )


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
    parser.add_argument(
        '--dimension',
        dest='dimension',
        default=None,
        help='Specify dimension/size of the map via `--dimension="width height"`, default 64x64'
    )
    parser.add_argument(
        '--resolution', '-res',
        dest='resolution',
        type=float,
        default=0.1,
        help='Specify resolution of the map, default 0.1m'
    )
    args, __ = parser.parse_known_args()

    try:
        if args.dimension is not None:
            args.dimension = [int(x) for x in args.dimension.split(" ")]
    except BaseException:
        print("err parsing dimension..")
        exit(2)

    main(args)
