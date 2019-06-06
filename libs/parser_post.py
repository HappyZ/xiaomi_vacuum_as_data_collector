#!/usr/bin/python

import io
import os
import sys
import pickle
from time import sleep

from PIL import Image
from PIL import ImageDraw
from PIL import ImageChops

import numpy as np
import matplotlib.pyplot as plt

from libs.tshark import Tshark


RED = (255, 0, 0, 255)
PICKLE_MAP_SIZE = 64   # num
PICKLE_MAP_STEP = 0.1  # meter
WALL_PENETRATION = -30.0  # dB
WALL_REFLECTION = -15.0  # dB
np.set_printoptions(threshold=sys.maxsize)


def get_groundtruth_dict(f_gt):
    gt = {}
    if f_gt is None:
        return gt
    with open(f_gt, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if '#' in line:
            continue
        tmp = line.rstrip('\n').split(',')
        addr = tmp[0]
        loc_x = float(tmp[1])
        loc_y = float(tmp[2])
        gt[addr] = np.array([loc_x, loc_y])
    return gt


def load_rss_data_with_pkt_types(fp: str, orientation: int) -> dict:
    '''
    split rss data into multiple types
    '''
    result = {}
    with open(fp, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if '#' in line:
            continue
        data = line.rstrip().split(',')
        pkt_type = int(data[9])
        if pkt_type not in result:
            result[pkt_type] = []
        # rotate at (0, 0), the dock location
        if (orientation % 4) is 0:
            loc_x = float(data[0])
            loc_y = float(data[1])
            orient = float(data[2]) % (2 * np.pi)
        elif (orientation % 4) is 1:
            loc_x = -float(data[1])
            loc_y = float(data[0])
            orient = (float(data[2]) - 0.5 * np.pi) % (2 * np.pi)
        elif (orientation % 4) is 2:
            loc_x = -float(data[0])
            loc_y = -float(data[1])
            orient = (float(data[2]) - np.pi) % (2 * np.pi)
        elif (orientation % 4) is 3:
            loc_x = float(data[1])
            loc_y = -float(data[0])
            orient = (float(data[2]) + 0.5 * np.pi) % (2 * np.pi)
        # only need to take x, y, RSS for now
        result[pkt_type].append([loc_x, loc_y, float(data[5]), orient])
    return result


def blocking_display_rss_map(
    rss_map: np.ndarray,
    visualize: bool = False,
    output_map: bool = False,
    vmin: float = -80.0,
    vmax: float = -40.0,
    fp: str = None
):
    '''
    '''
    plt.imshow(
        np.transpose(rss_map),
        cmap='hot',
        origin='lower',
        interpolation='nearest',
        vmin=vmin,
        vmax=vmax
    )
    plt.colorbar()
    # plt.show()
    plt.draw()
    if output_map:
        plt.savefig("{}.png".format(fp.replace("_map", "_floormap")), dpi=50)
    if visualize:
        plt.pause(0.1)
        q = input("press Enter to continue... type q to quit: ")
        if q == 'q':
            sys.exit()
    plt.close()


def convert_to_pickle_rss(
    fp: str, 
    orientation: int,
    labels: list = None,  # the right groundtruth in rss map pixels
    visualize: bool = False, 
    output_map: bool = False,
    filters: int = None,
    sampling: bool = False,
    map_dim: tuple = None,
    map_res: float = None
):
    '''
    modified from Zhuolin
    '''

    def find_index(array, lower, upper):
        return np.where((array >= lower) & (array <= upper))[0]

    # load data and split into different types
    results = load_rss_data_with_pkt_types(fp, orientation)

    # define map dimension
    if map_dim is None:
        map_dim = (PICKLE_MAP_SIZE, PICKLE_MAP_SIZE)

    if map_res is None:
        map_res = PICKLE_MAP_STEP

    # pick the most frequent type
    pkt_types = [(key, len(results[key])) for key in results.keys()]
    pkt_types = sorted(pkt_types, key=lambda x: x[1], reverse=True)
    print("most frequent data type is {} with {} pkts".format(pkt_types[0][0], pkt_types[0][1]))
    data = results[pkt_types[0][0]]

    # sort it and transpose it
    data = np.transpose(np.array(sorted(data, key = lambda x: (x[0], x[1]))))
    loc_x_min = min(data[0, :])
    loc_x_max = max(data[0, :])
    loc_y_min = min(data[1, :])
    loc_y_max = max(data[1, :])
    loc_x_center = (loc_x_min + loc_x_max) / 2.0
    loc_y_center = (loc_y_min + loc_y_max) / 2.0
    
    # convert it to a map
    rss_map = np.ones(map_dim) * -85.0
    factor = 0.75

    for i in range(map_dim[0]):
        # if i not in rss_map_dict:
        #     rss_map_dict[i] = {}
        # search for x_idx
        upper_bound_x = loc_x_center + map_res * (i - (map_dim[0] / 2) + 0.5)
        lower_bound_x = upper_bound_x - map_res
        data_x_idxs = find_index(
            data[0, :],
            lower_bound_x - factor * map_res,
            upper_bound_x + factor * map_res
        )
        data_part = data[:, data_x_idxs]
        if data_part.size is 0:
            continue
        data_y_idx = 0
        for j in range(map_dim[1]):
            # search for y_idx
            upper_bound_y = loc_y_center + map_res * (j - (map_dim[1] / 2) + 0.5)
            lower_bound_y = upper_bound_y - map_res
            data_y_idxs = find_index(
                data_part[1, :],
                lower_bound_y - factor * map_res,
                upper_bound_y + factor * map_res
            )
            data_fullfilled = data_part[2, data_y_idxs]
            orientation_fullfilled = data_part[3, data_y_idxs]
            if filters is 0:
                data_fullfilled = data_fullfilled[(orientation_fullfilled > 1.75 * np.pi) | (orientation_fullfilled < 0.25 * np.pi)]
            elif filters is 1:
                data_fullfilled = data_fullfilled[(orientation_fullfilled > 1.25 * np.pi) & (orientation_fullfilled < 1.75 * np.pi)]
            elif filters is 2:
                data_fullfilled = data_fullfilled[(orientation_fullfilled > 0.75 * np.pi) & (orientation_fullfilled < 1.25 * np.pi)]
            elif filters is 3:
                data_fullfilled = data_fullfilled[(orientation_fullfilled > 0.25 * np.pi) & (orientation_fullfilled < 0.75 * np.pi)]
            elif filters is 4:
                data_fullfilled = data_fullfilled[(orientation_fullfilled > 1.5 * np.pi) | (orientation_fullfilled < 0.5 * np.pi)]
            elif filters is 5:
                data_fullfilled = data_fullfilled[(orientation_fullfilled > 0.5 * np.pi) & (orientation_fullfilled < 1.5 * np.pi)]
            if data_fullfilled.size:
                if sampling:
                    rss_map[i, j] = max(np.random.choice(data_fullfilled, 1)[0], -85.0)
                else:
                    rss_map[i, j] = max(np.median(data_fullfilled), -85.0)

    filepath = fp.replace(
        ".csv", "{}_pkttype_{}_map{}"
        .format(
            "_s{}".format(np.random.randint(0, 999999)) if sampling else "",
            pkt_types[0][0], 
            "" if filters is None else "_{}".format(filters)
        )
    )

    if visualize or output_map:
        blocking_display_rss_map(rss_map, visualize=visualize, output_map=output_map, fp=filepath)

    with open("{}.pickle".format(filepath), "wb") as f:
        pickle.dump([rss_map, labels], f)


def extract_dev_from_combined(fp, minimalCounts=100, cleanup=True):
    '''
    extract each device data from combined file `fp`
    '''
    files = {}
    folderpath, ext = os.path.splitext(fp)

    try:
        os.mkdir(folderpath)
    except FileExistsError:
        pass
    except BaseException:
        raise

    with open(fp) as f:
        lines = f.readlines()

    for line in lines[1:]:
        tmp = line.rstrip().split(",")
        addr = tmp[3].replace(":", "")
        if addr not in files:
            files[addr] = []
        files[addr].append(",".join(tmp[:3] + tmp[4:]))

    for addr in list(files.keys()):
        if len(files[addr]) < minimalCounts:
            del files[addr]

    title = lines[0].rstrip().split(",")
    headline = ",".join(title[:3] + title[4:]) + "\n"
    filepaths = []

    for addr in files.keys():
        filepath = "{}/{}.csv".format(folderpath, addr)
        filepaths.append(filepath)
        with open(filepath, "w") as f:
            f.write(headline)
            for line in files[addr]:
                f.write("{}\n".format(line))

    if len(files) > 0 and cleanup:
        os.remove(fp)

    return filepaths


def combine_sig_loc(sig_fp, loc_fp):
    '''
    append location to signal data
    '''
    filename, ext = os.path.splitext(loc_fp)
    with open(sig_fp) as f:
        sig_data = f.readlines()
    with open(loc_fp) as f:
        loc_data = f.readlines()
    i_s = 1  # remove first line on info
    i_l = 1  # remove first line on info
    len_sig = len(sig_data)
    len_loc = len(loc_data)
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')
    outfile = "{0}_sig.csv".format(filename.rstrip("_loc"))
    with open(outfile, 'w') as f:
        f.write("#x,y,orient," + sig_data[0][1:])
        prev_i_s = 0
        prev_i_l = 0
        while i_s < len_sig:
            if prev_i_s != i_s:
                sig_tmp = sig_data[i_s].rstrip().split(',')
                prev_i_s = i_s
            if prev_i_l != i_l:
                loc_tmp = loc_data[i_l].rstrip().split(',')
                prev_i_l = i_l
            epoch_sig = float(sig_tmp[1])
            epoch_loc = float(loc_tmp[2]) / 1000.0
            x = float(loc_tmp[3])
            y = float(loc_tmp[4])
            if x > max_x:
                max_x = x
            if x < min_x:
                min_x = x
            if y > max_y:
                max_y = y
            if y < min_y:
                min_y = y
            orientation = float(loc_tmp[5])
            if epoch_sig > epoch_loc and i_l < len_loc - 1:
                i_l += 1
                continue
            f.write("{},{},{},{}\n".format(x, y, orientation, ",".join(sig_tmp)))
            i_s += 1
    return outfile, ((min_x, min_y), (max_x, max_y))


def translate_pcap(pcap_fp, is_csi):
    tshark = Tshark()
    filepath, ext = os.path.splitext(pcap_fp)
    outputfp = "{}.csv".format(filepath)
    if os.path.isfile(outputfp):
        return outputfp
    if is_csi:
        tshark.translateCSI(pcap_fp, outputfp)
    else:
        tshark.translatePcap(pcap_fp, outputfp)
    return outputfp


def normalize_rss(rss):
    rss = max(min(rss, -20), -85)
    return (rss + 85) / 65.0


def get_locs_from_parsed_sig_data(sig_data, is_csi=False):
    # loop each loc
    locs_data = []

    if is_csi:
        print("Not implemented yet")
        return locs_data

    for line in sig_data:
        tmp = line.rstrip().split(",")
        x = float(tmp[0])
        y = float(tmp[1])
        rss = float(tmp[4])
        # calculate color of rss
        color = (RED[0], RED[1], RED[2], int(255 * normalize_rss(rss)))
        pos = (x, y, color)
        locs_data.append(pos)
    return locs_data



def get_locs_from_slam_data(slam_data):
    # loop each loc
    locs_data = []
    for line in slam_data:
        tmp = line.rstrip().split(",")
        robotime = float(tmp[1])
        epoch = int(tmp[2])
        x = float(tmp[3])
        y = float(tmp[4])
        yaw = float(tmp[5])
        pos = (x, y, RED)
        locs_data.append(pos)
    return locs_data


def estimate_orientation(map_dim, reflections):
    orientations = np.empty(map_dim, dtype=float) * float('nan')
    for i in range(map_dim[0]):
        for j in range(map_dim[1]):
            if reflections[i, j] < -80.0:
                continue
            xs = []
            ys = []
            for off_i in range(-4, 5, 2):
                end_i = min(max(i + off_i, 0), map_dim[0]-1)
                for off_j in range(-4, 5, 2):
                    end_j = min(max(j + off_j, 0), map_dim[1]-1)
                    if reflections[end_i, end_j] > -100.0:
                        if end_i not in xs or end_j not in ys:
                            xs.append(end_i)
                            ys.append(end_j)
            if len(xs) is 0:
                continue
            if len(set(xs)) == 1:
                coefs = [None, 999.0]
            else:
                coefs = np.polynomial.polynomial.polyfit(xs, ys, 1)
            orientations[i, j] = round(np.arctan2(coefs[1], 1.0) * 180 / np.pi, 1)
    return orientations


def build_map(
    f_map,
    orientation,
    minmax_xys,
    markers=None,
    visualize=False,
    output_map=False,
    map_dim=None,
    map_res=None
):
    '''
    draws the path into the map. Returns the new map as a BytesIO
    modded from https://github.com/dgiese/dustcloud/blob/71f7af3e2b9607548bcd845aca251326128f742c/dustcloud/build_map.py
    '''
    grey = (125, 125, 125, 255)
    white = (255, 255, 255, 255)
    blue = (0, 0, 255, 255)
    pink = (255, 0, 255, 255)
    red = (255, 0, 0, 255)
    black = (0, 0, 0, 255)

    # define map dimension
    if map_dim is None:
        map_dim = (PICKLE_MAP_SIZE, PICKLE_MAP_SIZE)
    if map_res is None:
        map_res = PICKLE_MAP_STEP
    floor_map = np.zeros(map_dim)

    # define map center x,y
    center_x_val = (minmax_xys[1][0] + minmax_xys[0][0]) / 2
    center_y_val = (minmax_xys[1][1] + minmax_xys[0][1]) / 2

    # load map
    with open(f_map, 'rb') as f:
        map_image_data = f.read()

    map_image = Image.open(io.BytesIO(map_image_data))
    map_image = map_image.convert('RGBA')
    map_pix = map_image.load()

    # calculate center of the measurement
    center_x = int(map_image.size[0] / 2 + center_x_val * 20)
    center_y = int(map_image.size[1] / 2 - center_y_val * 20)

    for i in range(map_dim[0]):
        idx_x = center_x + map_res * 20 * (i - (map_dim[0] / 2))
        for j in range(map_dim[1]):
            idx_y = center_y - map_res * 20 * (j - (map_dim[1] / 2))
            is_blocked = False
            for kk in range(2):
                for ll in range(2):
                    color = map_pix[idx_x + kk, idx_y + ll]
                    is_blocked = is_blocked or (color in [black, blue, pink, red])
            if is_blocked:
                if orientation % 4 == 0:
                    floor_map[i, j] = 1
                elif orientation % 4 == 1:
                    floor_map[map_dim[1] - j - 1, i] = 1
                elif orientation % 4 == 2:
                    floor_map[map_dim[0] - i - 1, map_dim[1] - j - 1] = 1
                elif orientation % 4 == 3:
                    floor_map[j, map_dim[1] - i - 1] = 1
            elif color not in [grey, white]:
                print("unknown color: {}".format(color))

    filepath, ext = os.path.splitext(f_map)

    if visualize or output_map:
        blocking_display_rss_map(
            floor_map,
            visualize=visualize,
            output_map=output_map,
            fp=filepath,
            vmin=0.0,
            vmax=1.0
        )

    penetrations = floor_map * WALL_PENETRATION
    reflections = floor_map * WALL_REFLECTION
    reflections[reflections == 0] = -100.0
    orientations = estimate_orientation(map_dim, reflections)
    # blocking_display_rss_map(
    #     abs(orientations),
    #     visualize=visualize,
    #     output_map=output_map,
    #     fp=filepath+'ori',
    #     vmin=-10,
    #     vmax=100
    # )

    with open(filepath.replace("_map", "_floormap.pickle"), "wb") as f:
        pickle.dump([penetrations, reflections, orientations], f)


def test(args):
    if args.loc and args.map:
        with open(args.loc) as f:
            # skip the first line which is coumn names
            slam_data = f.readlines()[1:]
        locs_data = get_locs_from_slam_data(slam_data)
        with open(args.map, 'rb') as f:
            map_image_data = f.read()
        augmented_map = build_map(locs_data, map_image_data)
        filepath, ext = os.path.splitext(args.map)
        with open("{}.png".format(filepath), 'wb') as f:
            f.write(augmented_map.getvalue())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='post processing test'
    )

    parser.add_argument(
        '-l', '--location',
        dest='loc',
        default=None,
        help='Specify location file path'
    )

    parser.add_argument(
        '-m', '--map',
        dest='map',
        default=None,
        help='Specify map file path'
    )

    args, __ = parser.parse_known_args()

    test(args)
