import os
import time
import subprocess

from collections import OrderedDict


PLAYER_LOG_FILEPATH = "/run/shm/PLAYER_fprintf.log"
SLAM_LOG_FILEPATH = "/run/shm/SLAM_fprintf.log"


def line_parsing_player_log(log_line):
    '''
    parse the line from player log
    '''
    vals = log_line.split(" ")
    result = OrderedDict([
        ('type', vals[3]),
        ('robotime', float(vals[0])),
        ('epoch', int(time.time() * 1000)),
    ])
    if vals[3] == 'position2d':
        result['p_x'] = float(vals[7])      # meter
        result['p_y'] = float(vals[8])      # meter
        result['yaw'] = float(vals[9])      # radian
        result['v_x'] = float(vals[10])     # meter/s
        result['v_y'] = float(vals[11])     # meter/s
        result['v_yaw'] = float(vals[12])   # radian/s
    elif vals[3] == 'position3d':
        result['p_x'] = float(vals[7])  # meter
        result['p_y'] = float(vals[8])  # meter
        result['p_z'] = float(vals[9])  # meter
        result['roll'] = float(vals[10])  # radian
        result['pitch'] = float(vals[11])  # radian
        result['yaw'] = float(vals[12])  # radian
        result['v_x'] = float(vals[13])  # meter
        result['v_y'] = float(vals[14])  # meter
        result['v_z'] = float(vals[15])  # meter
        result['v_roll'] = float(vals[16])  # radian
        result['v_pitch'] = float(vals[17])  # radian
        result['v_yaw'] = float(vals[18])  # radian
    elif vals[3] == 'ir':
        result['counts'] = int(vals[7])
        result['ranges'] = [float(x) for x in vals[8:-1]]
    return result


def get_player_log(
    filepath=None,
    position2d=True,
    position3d=True,
    outputfile=None
):
    '''
    get player log and parse them into readable results
    @param filepath:    file path of the log, if not specified,
                        directly tail from PLAYER_LOG_FILEPATH
    @param position2d:  bool flag, whether parse position2d data
    @param position3d:  bool flag, whether parse position3d data
    @param outputfile:  output file to write to
    '''

    counter = 0
    line_idx = 0
    pos2d_data = []
    pos3d_data = []
    data = {
        'position2d': pos2d_data,
        'position3d': pos3d_data
    }

    filename = None
    fileext = None
    if outputfile:
        filename, fileext = os.path.splitext(outputfile)

    lines = []
    if filepath:
        if not os.path.isfile(filepath):
            print("{} does not exist".format(filepath))
            return data
        with open(filepath, "r") as f:
            lines = f.readlines()
    else:
        while not os.path.isfile(PLAYER_LOG_FILEPATH):
            time.sleep(1)
        subprocess.call("echo '' > {}".format(PLAYER_LOG_FILEPATH), shell=True)
        # tail the log file
        proc = subprocess.Popen(
            ['tail', '-F', PLAYER_LOG_FILEPATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    with open("{0}_2d{1}".format(filename, fileext), 'w') as outf:
        outf.write("#type,robotime,epoch,p_x,p_y,yaw,v_x,v_y,v_yaw\n")

    with open("{0}_3d{1}".format(filename, fileext), 'w') as outf:
        outf.write("#type,robotime,epoch,p_x,p_y,p_z,roll,pitch,yaw,v_x,v_y,v_z,v_roll,v_pitch,v_yaw\n")

    while 1:
        if filepath:
            # if reading from a file, end it at end of file
            if line_idx >= len(lines):
                break
            line = lines[line_idx].rstrip()
            line_idx += 1
        else:
            line = proc.stdout.readline().decode().rstrip()
        try:
            result = line_parsing_player_log(line)
        except KeyboardInterrupt:
            break
        except BaseException as e:
            print("error: {}".format(e))
            print(line)
            continue
        try:
            counter += 1
            if counter % 100 == 0:
                print("data line counter: {}".format(counter))
            if position2d and result['type'] == 'position2d':
                pos2d_data.append(result)
                if outputfile:
                    with open("{0}_2d{1}".format(filename, fileext), 'a+') as outf:
                        outf.write("{}\n".format(",".join([str(result[key]) for key in result])))
            elif position3d and result['type'] == 'position3d':
                pos3d_data.append(result)
                if outputfile:
                    with open("{0}_3d{1}".format(filename, fileext), 'a+') as outf:
                        outf.write("{}\n".format(",".join([str(result[key]) for key in result])))
        except KeyboardInterrupt:
            break
        except BaseException as e:
            raise

    return data


def line_parsing_slam_log(log_line):
    '''
    parse the line from slam log
    '''
    vals = log_line.split(" ")
    result = OrderedDict([
        ('type', vals[1]),
        ('robotime', float(vals[0])),
        ('epoch', int(time.time() * 1000)),
    ])
    if vals[1] == 'estimate':
        result['p_x'] = float(vals[2])
        result['p_y'] = float(vals[3])
        result['yaw'] = float(vals[4])
    return result


def get_slam_log(
    filepath=None,
    outputfile=None
):
    '''
    get SLAM log and parse them into readable results
    @param filepath:    file path of the log, if not specified,
                        directly tail from SLAM_LOG_FILEPATH
    @param outputfile:  output file to write to
    '''

    counter = 0
    line_idx = 0
    slam_data = []

    filename = None
    fileext = None
    if outputfile:
        filename, fileext = os.path.splitext(outputfile)

    lines = []
    if filepath:
        if not os.path.isfile(filepath):
            print("{} does not exist".format(filepath))
            return slam_data
        with open(filepath, "r") as f:
            lines = f.readlines()
    else:
        while not os.path.isfile(SLAM_LOG_FILEPATH):
            time.sleep(1)
        subprocess.call("echo '' > {}".format(SLAM_LOG_FILEPATH), shell=True)
        # tail the log file
        proc = subprocess.Popen(
            ['tail', '-F', SLAM_LOG_FILEPATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    with open("{0}_slam{1}".format(filename, fileext), 'w') as outf:
        outf.write("#type,robotime,epoch,p_x,p_y,yaw\n")

    while 1:
        if filepath:
            # if reading from a file, end it at end of file
            if line_idx >= len(lines):
                break
            line = lines[line_idx].rstrip()
            line_idx += 1
        else:
            line = proc.stdout.readline().decode().rstrip()
        try:
            result = line_parsing_slam_log(line)
        except KeyboardInterrupt:
            break
        except BaseException as e:
            print("error: {}".format(e))
            print(line)
            continue
        try:
            if result['type'] == 'estimate':
                counter += 1
                if counter % 100 == 0:
                    print("data line counter: {}".format(counter))
                slam_data.append(result)
                if outputfile:
                    with open("{0}_slam{1}".format(filename, fileext), 'a+') as outf:
                        outf.write("{}\n".format(",".join([str(result[key]) for key in result])))
        except KeyboardInterrupt:
            break
        except BaseException as e:
            raise

    return slam_data



def test(args):
    if args.slam:
        get_slam_log(
            filepath=args.filepath,
            outputfile=args.of
        )
    if args.pos2d or args.pos3d:
        get_player_log(
            filepath=args.filepath,
            position2d=args.pos2d,
            position3d=args.pos3d,
            outputfile=args.of
        )


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description='parser test'
    )
    parser.add_argument(
        '-f', '--filepath',
        dest='filepath',
        default=None,
        help='Specify input file path'
    )
    parser.add_argument(
        '-o', '--output',
        dest='of',
        default=None,
        help='Specify output file path'
    )
    parser.add_argument(
        '-slam', '--slam-estimated',
        dest='slam',
        action='store_true',
        help='Get SLAM estimated positions'
    )
    parser.add_argument(
        '-2d', '--position2d',
        dest='pos2d',
        action='store_true',
        help='Get 2d positions'
    )
    parser.add_argument(
        '-3d', '--position3d',
        dest='pos3d',
        action='store_true',
        help='Get 3d positions'
    )

    args, __ = parser.parse_known_args()

    test(args)