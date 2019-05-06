import io
import os
from PIL import Image
from PIL import ImageDraw
from PIL import ImageChops

from libs.tshark import Tshark


RED = (255, 0, 0, 255)


def extract_dev_from_combined(fp, minimalCounts=100, cleanup=True):
    '''
    extract each device data from combined file `fp`
    '''
    files = []
    counters = []
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
        addr = tmp[2].replace(":", "")
        if addr not in files:
            files.append(addr)
            counters.append(1)
        else:
            counters[files.index(addr)] += 1

    for i in range(len(counters)-1, -1, -1):
        if counters[i] < minimalCounts:
            counters.pop(i)
            files.pop(i)

    title = lines[0].rstrip().split(",")
    filepaths = ["{}/{}.csv".format(folderpath, file) for file in files]
    for filepath in filepaths:
        with open(filepath, "w") as f:
            f.write(",".join(title[:2] + title[3:]) + "\n")

    for line in lines[1:]:
        tmp = line.rstrip().split(",")
        addr = tmp[2].replace(":", "")
        if addr not in files:
            continue
        filepath = filepaths[files.index(addr)]
        with open(filepath, "a+") as f:
            f.write(",".join(tmp[:2] + tmp[3:]) + "\n")
    
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
        f.write("#x,y," + sig_data[0][1:])
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
            if epoch_sig > epoch_loc:
                i_l += 1
                if i_l >= len_loc:
                    i_l = len_loc - 1
                continue
            f.write("{},{},{}\n".format(x, y, ",".join(sig_tmp)))
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
