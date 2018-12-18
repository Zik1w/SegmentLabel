import sys
import getopt
import os
import struct
import datetime
import math
import json
import csv
import numpy as np
import sqlite3
import collections

from collections import Counter



class SegmentLabel(object):
    def __init__(self, label_file, weight_file, th=None, config_file=None):
        self.index_map = self._objectIndexVector(label_file)
        self.weight_vector = self._objectWeightVector(weight_file)
        self.object_prev_vector = None
        self.object_var_vector = None
        self.temporal_prev_vector = None
        self.temporal_var_vector = None
        self.spatial_prev_vector = None
        self.spatial_cur_vector = None


        self.seg_num = 0
        self.frame_cnt = 0.0
        self.initilized = False
        self.initial_frame = None
        self.last_frame = None
        self.duration = 0
        self.duration_highpass = 40
        self.last_segmented_frame = None
        self.conn = sqlite3.connect('seglab.db')
        self.frame_info = Counter()
        self.hash_frames = {}
        self.hash_begin_frame = {}
        self.hash_begin_frame = {}
        self.hash_frame_info = {}


        self.confidence_filter_param = 0.05
        self.weight_param = 1.0
        self.object_param = 1.0
        self.temporal_param = 1.0
        self.spatial_param = 1.0
        self.growth_rate = 0.01
        self.time_change_rate = 1
        self.add_param = 1.0
        self.remove_param = 1.0
        self.thresold_sum_option = 1     #0 for L1-norm, 1 for L2-norm
        self.thresold_ratio = 3
        self.class_ratio = 0.01

        if th:
            self.thresold_param = th
        else:
            # self.thresold_param = 0.2
            self.thresold_param = 0.00000001   # single frame scene
        self.readConfig(config_file)


        c_init = self.conn.cursor()

        c_init.execute("drop table if exists seglab")

        c_init.execute('''CREATE TABLE IF NOT EXISTS seglab
                     (Start TEXT, Frame TEXT, Date DATE, Run TEXT, Scene TEXT, Class TEXT, Label TEXT, Prob REAL, Location REAL, 
                     PRIMARY KEY(Start, Frame, Class, Label))''')

        c_init.close()


    @staticmethod
    def _objectIndexVector(label_file):
        index_map = {}
        with open(label_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                index_map[row['label']] = int(row['Number'])
        # print(len(index_map))
        return index_map

    def updateIndex(self, label_file):
        tmp_index_map = {}
        with open(label_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                tmp_index_map[int(row['label'])] = row['Number']
        self.index_map = tmp_index_map


    def _objectWeightVector(self, weight_file):
        weight_vector = np.ones(len(self.index_map))
        with open(weight_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                weight_vector[int(row['Number'])-1] = row['Weight']
        return weight_vector


    def updateWeight(self, weight_file):
        tmp_weight_vector = np.ones(len(self.index_map))
        with open(weight_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                tmp_weight_vector[int(row['Number'])-1] = row['Weight']
        self.weight_vector = tmp_weight_vector

    def objectEncodingVector(self, ann):
        temp_object_vector = np.zeros(len(self.index_map))

        for item in ann:
            if item['prob'] >= self.confidence_filter_param:
                temp_object_vector[self.index_map[item['label']]-1] += 1

        # print("object vector:", temp_object_vector)
        return temp_object_vector

    def objectFrequencyEncodingVector(self, ann):
        temp_object_vector = np.zeros(len(self.index_map))


        for k, v in ann.items():
            temp_object_vector[self.index_map[k]] = int(v)

        # print("object vector:", temp_object_vector)
        return temp_object_vector

    def spatialWeightVector(self, ann):
        tmp_sw_vector = np.zeros(len(self.index_map))
        tmp_cnt_vector = np.zeros(len(self.index_map))

        for k in ann:
            tmp_sw_vector[self.index_map[k['label']]-1] += (k["xright"] - k["xleft"]) * (k["ybottom"] - k["ytop"])
            tmp_cnt_vector[self.index_map[k['label']]-1] += 1

        return np.divide(tmp_sw_vector, tmp_cnt_vector, out=tmp_sw_vector, where=tmp_cnt_vector != 0)

    def temporalWeightVector(self, object_prev_vector):
        tmp_tp_vector = np.ones(len(self.index_map))

        # if self.initilized:
        #     for k in range(len(object_prev_vector)):
        #         if object_prev_vector[k] > 0:
        #             tmp_tp_vector[k] += self.time_change_rate
        #         else:
        #             tmp_tp_vector[k] = 1

        # print("over time vector:", tmp_tp_vector)
        return tmp_tp_vector

    def temporalVariationVector(self, object_prev_vector, object_cur_vector):
        tmp_tp_vector = np.ones(len(self.index_map))

        # for k in range(len(object_prev_vector)):
        #     if object_prev_vector[k] > 0 and object_cur_vector[k] > 0 and object_cur_vector[k] >= object_prev_vector[k]:
        #         tmp_tp_vector[k] = (object_cur_vector[k] - object_prev_vector[k]) * self.time_change_rate
        #         # tmp_tp_vector[k] *= 1 + self.growth_rate
        #     elif object_prev_vector[k] > 0 and object_cur_vector[k] > 0 and object_cur_vector[k] < object_prev_vector[k]:
        #         tmp_tp_vector[k] = (object_prev_vector[k] - object_cur_vector[k]) * self.time_change_rate
        #     else:
        #         tmp_tp_vector[k] = 1

        # print("time-based change vector:", tmp_tp_vector)
        return tmp_tp_vector


    def objectVariationVector(self, prev, current):
        tem_var_vector = np.zeros(len(self.index_map))

        for k in range(len(prev)):
            if prev[k] > current[k]:
                tem_var_vector[k] = self.remove_param * (prev[k] - current[k])
            elif prev[k] < current[k]:
                tem_var_vector[k] = self.add_param * (current[k] - prev[k])

        return tem_var_vector


    def dissimiliarityVector(self, ft, f, tt, t, sp, sc):

        return self.object_param*(np.divide(ft, f, out=ft, where=f != 0)) \
               * self.temporal_param*np.divide(tt, t, out=tt, where=t != 0) \
               * self.weight_param * self.weight_vector
               # * self.spatial_param*np.divide(sp, sc, out=np.zeros_like(sp), where=sc != 0) \


    def dissimiliarityVector_simple(self, ft, f, tt, t):
        tmp_dm =  self.object_param*(np.divide(ft, f, out=ft, where=f != 0)) \
               * self.temporal_param*(np.divide(tt, t, out=tt, where=t != 0)) \
               * self.weight_param * self.weight_vector

        # print(tmp_dm)
        return tmp_dm



    ##change to add more information to send to playdetect
    def labeling(self, first, last, table):
        frame_duration = int(last["playbackNo"]) - int(first["playbackNo"])
        #print(frame_time_start) 
        data_object = {"info": [], "start": first["frameName"], "end": last["frameName"], "duration": frame_duration}
        for k, v in table.items():
            data_object["info"].append({"label": k, "frequency": v / self.frame_cnt})
        # print(data_object)
        # data_json = json.dumps(data_object)
        return data_object

    # def label_seg(self, first, last, table):
    #     data_object = {"info": [], "start": first["frameName"], "end": last["frameName"]}
    #     for k, v in table.items():
    #         data_object["info"].append({"label": k, "frequency": v})
    #     # data_json = json.dumps(data_object)
    #     return data_object

    def thresold_check(self, dm):


        if self.thresold_sum_option:
            # metric_dm = np.sqrt(dm.dot(dm))/(self.thresold_ratio*pow(len(self.index_map), self.class_ratio))
            metric_dm = np.sqrt(dm.dot(dm)) / (self.thresold_ratio*(len(self.index_map) * self.class_ratio))
        else:
            metric_dm = dm.sum()/(self.thresold_ratio*(len(self.index_map) * self.class_ratio))

        # print(metric_dm)

        if max(0, metric_dm) < self.thresold_param or self.duration < self.duration_highpass:
            return False
        else:
            return True


    def processAnnotation(self, curr):

        # print("current frame is:")
        # print(curr)

        c = self.conn.cursor()

        # curr = []
        # for line in open(ann_file, 'r'):
        #     curr.append(json.loads(line))

        # for ann in curr:
        #     temp = []
        #     frameName = ann['frameName']
        #     for k in ann["annotations"]:
        #         temp.append({"label": ''.join([i for i in k["label"] if not i.isdigit()]), "ytop": k["ytop"],
        #                      "ybottom": k["ybottom"], "xleft": k["xleft"], "xright": k["xright"], "prob": k["prob"],
        #                      "frameName": frameName})
        #     curr_list.append(temp)
        # self.hash_frames[self.initial_frame['frameName']] = Counter()
        anno_table = Counter()
        sceneSeg = None
        if not self.initilized:
            self.initial_frame = curr
            self.last_frame = self.initial_frame
            self.frame_cnt += 1
            self.duration += 1

            entries = []
            ann = self.initial_frame["annotations"]
            for item in ann:
                if item['prob'] >= self.confidence_filter_param:
                    anno_table[item['label']] += 1
                    # self.hash_frames[self.initial_frame['frameName']][item['label']] += 1
                    temp_entry = (self.initial_frame['frameName'], self.initial_frame['frameName'], None, None, None, item['label'], str(anno_table[item['label']]), item['prob'], None)
                    entries.append(temp_entry)

            self.hash_frames[self.initial_frame['frameName']] = anno_table
            self.frame_info = anno_table

            # print(anno_table)
            # print(self.hash_frames)

            #c.executemany('INSERT INTO seglab VALUES (?,?,?,?,?,?,?,?,?)', entries)

            #generate the combined label result
            frame_ann = self.updateFrameAnno(ann)

            self.object_prev_vector = self.objectEncodingVector(frame_ann)
            self.spatial_prev_vector = self.spatialWeightVector(frame_ann)
            self.temporal_prev_vector = self.temporalWeightVector(self.object_prev_vector)
            self.initilized = True


        else:
            curr_frame = curr
            self.frame_cnt += 1
            self.duration += 1

            entries = []
            ann = curr_frame["annotations"]
            anno_table = Counter()
            # if not self.hash_frames.get(curr_frame["frameName"]):
            #     self.hash_frames[self.initial_frame["frameName"]] = anno_table
            # else:
            #     anno_table = self.hash_frames[self.initial_frame["frameName"]]

            for item in ann:
                if item['prob'] >= self.confidence_filter_param:
                    anno_table[item['label']] += 1
                    # if curr_frame['frameName'] not in self.hash_frames:
                    #     self.hash_frames[self.initial_frame['frameName']] = {}
                    #
                    # self.hash_frames[self.initial_frame['frameName']][item['label']] += 1
                    temp_entry = (self.initial_frame['frameName'], curr_frame['frameName'], None, None, None, item['label'], str(anno_table[item['label']]), item['prob'], None)
                    entries.append(temp_entry)

            # if curr_frame['frameName'] not in self.hash_frames:
            #     self.hash_frames[curr_frame['frameName']] = anno_table
            # else:
            #     for k, v in anno_table.items():
            #         self.hash_frames[curr_frame['frameName']][k] += v

            # self.hash_frames[self.initial_frame['frameName']] += anno_table

            # print(anno_table)
            for k, v in anno_table.items():
                self.frame_info[k] += v
            # print(self.frame_info)

            #c.executemany('INSERT INTO seglab VALUES (?,?,?,?,?,?,?,?,?)', entries)

            # print(self.hash_frames)
            # sceneSeg_list = self.processFrames(self.hash_frames)

            tmp_prev_object = self.object_prev_vector
            # tmp_spatial = self.spatial_prev_vector
            tmp_temporal = self.temporal_prev_vector

            #generate the combined label result
            frame_ann = self.updateFrameAnno(ann)


            self.object_prev_vector = self.objectEncodingVector(frame_ann)

            # self.spatial_prev_vector = self.spatialWeightVector(frame_ann)
            self.temporal_prev_vector = self.temporalWeightVector(self.object_prev_vector)

            self.object_var_vector = self.objectVariationVector(tmp_prev_object, self.object_prev_vector)
            self.temporal_var_vector = self.temporalVariationVector(tmp_temporal, self.temporal_prev_vector)

            ##detect scene change
            if self.thresold_check(self.dissimiliarityVector_simple(self.object_var_vector, tmp_prev_object, self.temporal_var_vector, tmp_temporal)):
                print(self.duration)
                sceneSeg = self.labeling(self.initial_frame, self.last_frame, self.frame_info)
                self.seg_num += 1
                self.frame_cnt = 0.0
                self.duration = 0
                self.initial_frame = curr_frame
                self.last_frame = self.initial_frame
                self.frame_info = anno_table

            self.last_frame = curr_frame
            self.last_segmented_frame = curr_frame

        #print(sceneSeg)
        # c.close()
        self.conn.commit()
        if sceneSeg:
            return sceneSeg
        else:
            # print("no scene change detected!")
            return []

    def readConfig(self, config_file):
        if config_file:
            with open(config_file) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row["Param"] == "Weight":
                        self.weight_param = float(row["Value"])
                    if row["Param"] == "Object":
                        self.object_param = float(row["Value"])
                    if row["Param"] == "Time":
                        self.temporal_param = float(row["Value"])
                    if row["Param"] == "Size":
                        self.spatial_param = float(row["Value"])
                    if row["Param"] == "Overtime":
                        self.growth_rate = float(row["Value"])
                    if row["Param"] == "Framerate":
                        self.time_change_rate = float(row["Value"])
                    if row["Param"] == "WeightForAdd":
                        self.add_param = float(row["Value"])
                    if row["Param"] == "WeightForRemove":
                        self.remove_param = float(row["Value"])
                    if row["Param"] == "Sum":
                        self.thresold_sum_option = int(row["Value"])
                    if row["Param"] == "FrequenceThresold":
                        self.thresold_ratio = float(row["Value"])
                    if row["Param"] == "ClassRatio":
                        self.class_ratio = float(row["Value"])
                    if row["Param"] == "Thresold":
                        self.thresold_param = float(row["Value"])


    def updateFrameAnno(self, annotations):
        return annotations


    def processFrames(self, hash_f):
        sceneSeg_list = []
        for fn, ann in hash_f.items():
            #print(fn)
            #print(ann)
            frame_ann = ann

            tmp_prev_object = self.object_prev_vector
            # tmp_spatial = self.spatial_prev_vector
            tmp_temporal = self.temporal_prev_vector

            self.object_prev_vector = self.objectFrequencyEncodingVector(frame_ann)
            # self.spatial_prev_vector = self.spatialWeightVector(frame_ann)
            self.temporal_prev_vector = self.temporalWeightVector(frame_ann)

            self.object_var_vector = self.objectVariationVector(tmp_prev_object, self.object_prev_vector)
            self.temporal_var_vector = self.temporalVariationVector(tmp_temporal, self.temporal_prev_vector)

            ##detect scene change
            if self.thresold_check(self.dissimiliarityVector_simple(self.object_var_vector, tmp_prev_object, self.temporal_var_vector, tmp_temporal)):
                # sceneSeg = self.label_seg(f)

                data_object = {"info": [], "start": self.hash_begin_frame, "end": fn}
                for k, v in ann.items():
                    data_object["info"].append({"label": k, "frequency": v})
                # data_json = json.dumps(data_object)
                # print(data_object)


                sceneSeg_list.append(json.dumps(sceneSeg))
                self.hash_begin_frame = curr_frame
                self.seg_num += 1

            self.last_segmented_frame = curr_frame

        return sceneSeg_list


    def resultFigure(self):
        pass

    def sceneDetection(self, ann):
        return self.processAnnotation(ann)

