import csv
import numpy as np
import sys
import pickle
import matplotlib.pyplot as plt
import bisect
np.set_printoptions(threshold=sys.maxsize)

types = []
type_values = []
xy_locs_rss = np.empty([1,3])
rss_map = np.empty([64, 64])
picked_type = -1

def main():
    if sys.argv[1] == "-help":
        print("usage: python3 rss_map_parser.py path/to/file/filename.csv -v/-h (vertical/horizontal map orientation) -d/-v/-dv (download/&visulize parsed rss map)")
    else:
        pathtofile = sys.argv[1]
        orientation = sys.argv[2]
        operation = sys.argv[3]
        find_type(pathtofile)
        if orientation == '-h':
            readCSV_h(pathtofile)
        elif orientation == '-v':
            readCSV_v(pathtofile)
        parse_map()

        if operation == '-d':
            write_pickle(pathtofile)
        elif operation == '-v':
            visualize_map()
        elif operation == '-dv':
            write_pickle(pathtofile)
            visualize_map()

def find_type(pathtofile):
    global type_values
    global picked_type
    with open(pathtofile) as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',')
        for row in csv_reader:
            if row[1]=='y':
                continue
            if len(types)==0:
                types.append(row[8])
                type_values.append(1)
            elif row[8] in types:
                type_values[types.index(row[8])] += 1
            else:
                types.append(row[8])
                type_values.append(1)

    picked_type = types[type_values.index(max(type_values))]

def readCSV_v(pathtofile):
    global xy_locs_rss
    global picked_type
    with open(pathtofile) as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',')
        for row in csv_reader:
            if row[8]==picked_type:
                x_loc = float(row[0])
                y_loc = float(row[1])
                rss = float(row[4])
                xy_locs_rss = np.vstack([xy_locs_rss, [x_loc, y_loc, rss]])

    xy_locs_rss = sorted(xy_locs_rss, key=lambda x: x[0])
    xy_locs_rss = np.transpose(xy_locs_rss)

def readCSV_h(pathtofile):
    global xy_locs_rss
    global picked_type
    with open(pathtofile) as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',')
        for row in csv_reader:
            if row[8]==picked_type:
                x_loc = float(row[1])
                y_loc = -float(row[0])
                rss = float(row[4])
                xy_locs_rss = np.vstack([xy_locs_rss, [x_loc, y_loc, rss]])

    xy_locs_rss = sorted(xy_locs_rss, key=lambda x: x[0])
    xy_locs_rss = np.transpose(xy_locs_rss)

def parse_map():
    global rss_map
    rss_sum_count = 0
    rss_sum_temp = 0
    for i in range(64):
        for ii in range(64):
            upper_bound_x = (-3.2+0.1*i+0.1)
            lower_bound_x = (-3.2+0.1*(i-1)-0.1)
            lower_bound_iii = bisect.bisect_left(xy_locs_rss[0,:], lower_bound_x)
            upper_bound_iii = bisect.bisect_right(xy_locs_rss[0,:], upper_bound_x, lo=lower_bound_iii)
            nums = xy_locs_rss[:, lower_bound_iii:upper_bound_iii]
            for iii in range(len(nums[0,:])):
                if nums[1,iii]>(5.8-0.1*ii-0.025) and nums[1,iii]<=(5.8-0.1*(ii-1)+0.025):
                    rss_sum_temp += nums[2,iii]
                    rss_sum_count += 1
            if rss_sum_count != 0:
                rss_map[i,ii] = rss_sum_temp / rss_sum_count
            else:
                rss_map[i,ii] = -85
            rss_sum_temp = 0
            rss_sum_count = 0

    rss_map = np.transpose(rss_map)

def write_pickle(pathtofile):
    file = open(pathtofile+".pickle", 'wb')
    pickle.dump(rss_map, file)
    file.close()

def visualize_map():
    plt.imshow(rss_map, cmap='hot', interpolation='nearest')
    plt.colorbar()
    plt.show()

main()

#def parse_horizontal_map():
#    global rss_map
#    rss_sum_count = 0
#    rss_sum_temp = 0
#    for i in range(64):
#        for ii in range(64):
#            upper_bound_x = (-5.8+0.1*i+0.025)
#            lower_bound_x = (-5.8+0.1*(i-1)-0.025)
#            lower_bound_iii = bisect.bisect_left(xy_locs_rss[0,:], lower_bound_x)
#            upper_bound_iii = bisect.bisect_right(xy_locs_rss[0,:], upper_bound_x, lo=lower_bound_iii)
#            nums = xy_locs_rss[:, lower_bound_iii:upper_bound_iii]
#            for iii in range(len(nums[0,:])):
#                if nums[1,iii]>(3.2-0.1*ii-0.075) and nums[1,iii]<=(3.2-0.1*(ii-1)+0.075):
#                    rss_sum_temp += nums[2,iii]
#                    rss_sum_count += 1
#            if rss_sum_count != 0:
#                rss_map[i,ii] = rss_sum_temp / rss_sum_count
#            else:
#                rss_map[i,ii] = -85
#            rss_sum_temp = 0
#            rss_sum_count = 0

#    rss_map = np.transpose(rss_map)
