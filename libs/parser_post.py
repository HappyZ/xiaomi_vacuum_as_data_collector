import io
import os
from PIL import Image
from PIL import ImageDraw
from PIL import ImageChops



def build_map(slam_data, map_image_data):
    '''
    draws the path into the map. Returns the new map as a BytesIO

    from https://github.com/dgiese/dustcloud/blob/71f7af3e2b9607548bcd845aca251326128f742c/dustcloud/build_map.py

    '''
    map_image = Image.open(io.BytesIO(map_image_data))
    map_image = map_image.convert('RGBA')

    # calculate center of the image
    center_x = map_image.size[0] / 2
    center_y = map_image.size[0] / 2

    # rotate image by -90°
    # map_image = map_image.rotate(-90)

    red = (255, 0, 0, 255)
    green = (0, 255, 0, 255)
    grey = (125, 125, 125, 255)  # background color
    transparent = (0, 0, 0, 0)

    # prepare for drawing
    draw = ImageDraw.Draw(map_image)

    # loop each loc
    prev_pos = None
    for line in slam_data:
        tmp = line.rstrip().split(",")
        robotime = float(tmp[1])
        epoch = int(tmp[2])
        x = float(tmp[3])
        y = float(tmp[4])
        yaw = float(tmp[5])

        # set x & y by center of the image
        # 20 is the factor to fit coordinates in in map
        x = center_x + (x * 20)
        y = center_y + (-y * 20)
        pos = (x, y)

        if prev_pos:
            draw.line([prev_pos, pos], red)

        prev_pos = pos

    # rotate image back by 90°
    # map_image = map_image.rotate(90)

    # crop image
    bgcolor_image = Image.new('RGBA', map_image.size, grey)
    cropbox = ImageChops.subtract(map_image, bgcolor_image).getbbox()

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
        with open(args.map, 'rb') as f:
            map_image_data = f.read()
        augmented_map = build_map(slam_data, map_image_data)
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
