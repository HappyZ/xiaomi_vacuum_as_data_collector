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
np.set_printoptions(threshold=sys.maxsize)



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


def blocking_display_rss_map(rss_map: np.ndarray, visualize: bool = False, output_map: bool = False, fp: str = None):
    '''
    '''
    plt.imshow(
        np.transpose(rss_map),
        cmap='hot',
        origin='lower',
        interpolation='nearest',
        vmin=-80.0,
        vmax=-40.0
    )
    plt.colorbar()
    # plt.show()
    plt.draw()
    if output_map:
        plt.savefig("{}.png".format(fp), dpi=50)
    if visualize:
        plt.pause(0.1)
        q = input("press Enter to continue... type q to quit: ")
        if q == 'q':
            sys.exit()
    plt.close()
    print()


def convert_to_pickle_rss(
    fp: str, 
    orientation: int,
    visualize: bool = False, 
    output_map: bool = False,
    filters: int = None,
    sampling: bool = False
):
    '''
    modified from Zhuolin
    '''

    def find_index(array, lower, upper):
        return np.where((array >= lower) & (array <= upper))[0]

    # load data and split into different types
    results = load_rss_data_with_pkt_types(fp, orientation)

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
    # rss_map_dict = {}
    rss_map = np.ones((PICKLE_MAP_SIZE, PICKLE_MAP_SIZE)) * -85.0
    factor = 0.75

    for i in range(PICKLE_MAP_SIZE):
        # if i not in rss_map_dict:
        #     rss_map_dict[i] = {}
        # search for x_idx
        upper_bound_x = loc_x_center + PICKLE_MAP_STEP * (i - (PICKLE_MAP_SIZE / 2) + 0.5)
        lower_bound_x = upper_bound_x - PICKLE_MAP_STEP
        data_x_idxs = find_index(
            data[0, :],
            lower_bound_x - factor * PICKLE_MAP_STEP,
            upper_bound_x + factor * PICKLE_MAP_STEP
        )
        data_part = data[:, data_x_idxs]
        if data_part.size is 0:
            continue
        data_y_idx = 0
        for j in range(PICKLE_MAP_SIZE):
            # search for y_idx
            upper_bound_y = loc_y_center + PICKLE_MAP_STEP * (j - (PICKLE_MAP_SIZE / 2) + 0.5)
            lower_bound_y = upper_bound_y - PICKLE_MAP_STEP
            data_y_idxs = find_index(
                data_part[1, :],
                lower_bound_y - factor * PICKLE_MAP_STEP,
                upper_bound_y + factor * PICKLE_MAP_STEP
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
        ".csv", "{}_pkt_{}_map{}_{}"
        .format(
            "_s{}".format(np.random.randint(0, 999999)) if sampling else "",
            pkt_types[0][0], 
            "" if filters is None else "_{}".format(filters),
            "h" if (orientation % 2) is 0 else "v"
        )
    )

    if visualize or output_map:
        blocking_display_rss_map(rss_map, visualize=visualize, output_map=output_map, fp=filepath)

    with open("{}.pickle".format(filepath), "wb") as f:
        pickle.dump(rss_map, f)


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
            orientation = float(loc_tmp[5])
            if epoch_sig > epoch_loc and i_l < len_loc - 1:
                i_l += 1
                continue
            f.write("{},{},{},{}\n".format(x, y, orientation, ",".join(sig_tmp)))
            i_s += 1
    return outfile


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


def build_map(locs_data, map_image_data):
    '''
    draws the path into the map. Returns the new map as a BytesIO
    modded from https://github.com/dgiese/dustcloud/blob/71f7af3e2b9607548bcd845aca251326128f742c/dustcloud/build_map.py
    '''

    def align_xy(xy, center_x, center_y):
        # set x & y by center of the image
        # 20 is the factor to fit coordinates in in map
        x = center_x + (xy[0] * 20)
        y = center_y + (-xy[1] * 20)
        return (x, y)


    map_image = Image.open(io.BytesIO(map_image_data))
    map_image = map_image.convert('RGBA')

    # calculate center of the image
    center_x = map_image.size[0] / 2
    center_y = map_image.size[0] / 2

    # rotate image by -90°
    # map_image = map_image.rotate(-90)

    grey = (125, 125, 125, 255)  # background color
    transparent = (0, 0, 0, 0)

    # prepare for drawing
    draw = ImageDraw.Draw(map_image)

    # loop each loc
    prev_xy = None
    for loc in locs_data:
        xy = align_xy(loc[:2], center_x, center_y)
        if prev_xy:
            draw.line([prev_xy, xy], loc[2])
        prev_xy = xy

    # rotate image back by 90°
    # map_image = map_image.rotate(90)

    # crop image
    bgcolor_image = Image.new('RGBA', map_image.size, grey)
    cropbox = ImageChops.subtract(map_image, bgcolor_image).getbbox()
    map_image = map_image.crop(cropbox)

    # and replace background with transparent pixels
    pixdata = map_image.load()
    for y in range(map_image.size[1]):
        for x in range(map_image.size[0]):
            if pixdata[x, y] == grey:
                pixdata[x, y] = transparent

    temp = io.BytesIO()
    map_image.save(temp, format="png")
    return temp


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
