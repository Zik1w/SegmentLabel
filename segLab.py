import sys
import getopt
import os
import struct
import datetime
import json
import operator


from copy import deepcopy
from pprint import pprint
from collections import Counter


def main(jSONFile):
    plt.imshow(np.random.random((50, 50)))
    plt.colorbar()
    plt.show()


    run_seq_no = 1
    prefix = '/ndn/eb/run/1/segment/' + str(run_seq_no) + '/segment/'
    seq_num = 1
    curr = []
    for line in open(jSONFile, 'r'):
        curr.append(json.loads(line))

    curr_list = []
    prev = []
    for ann in curr:
        temp = []
        frameName = ann['frameName']
        for k in ann["annotations"]:
            temp.append({"label": ''.join([i for i in k["label"] if not i.isdigit()]), "frameName": frameName})

        curr_list.append(temp)

    frame_list = []
    initial_frame = curr_list[0]
    last_frame = initial_frame
    frame_table = Counter()
    for item in initial_frame:
        frame_table[item['label']] += 1

    # print(frame_table)

    for k in curr_list:
        ann_table = Counter()
        for item in k:
            ann_table[item['label']] += 1

        # print(ann_table)


        if not segmentDetection(frame_table, ann_table):
            frame_list.append(labeling(initial_frame, last_frame, frame_table))
            seg_name = prefix + str(seq_num)
            seq_num += 1
            print(seg_name)
            initial_frame = k
            last_frame = initial_frame
            frame_table = ann_table
        else:
            last_frame = k

    print(frame_list)
    return frame_list


def labeling(first, last, table):
    data_object = {"labels": [], "start": first[-1]["frameName"], "end": last[-1]["frameName"]}
    for k, v in table.items():
        data_object["labels"].append({"item": k, "frequency": v})
    data_json = json.dumps(data_object)
    print(data_json)
    return data_json


def distanceCalculation():
    pass


def segmentDetection(f_table, a_table):
    common_count = 0
    common_item = 0
    total_count = 0
    total_item = 0
    # print(a_table)
    for it, n in a_table.items():
        common_count += min(n, f_table[it])
        if common_count > 0:
            common_item += 1
        total_item += 1
        total_count += n

    if common_count / total_count > 0.8:
        return True
    elif common_item / total_item > 0.9:
        return True
    elif common_count / total_count + common_item / total_item > 1:
        return True
    else:
        return False


if __name__ == '__main__':
    main(sys.argv[1])
