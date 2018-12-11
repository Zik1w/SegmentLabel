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
from collections import Counter



class SegmentLabel(object):
    def __init__(self, label_file, weight_file, configure_file = None):
        self.index_map = self._objectIndexVector(label_file)
        self.weight_vector = self._objectWeightVector(weight_file)
        self.object_prev_vector = None
        self.object_var_vector = None
        self.temporal_prev_vector = None
        self.temporal_var_vector = None
        self.spatial_prev_vector = None
        self.spatial_cur_vector = None
        self.weight_param = 1.0
        self.object_param = 1.0
        self.temporal_param = 1.0
        self.spatial_param = 1.0
        self.growth_rate = 0.01
        self.time_change_rate = 30.0
        self.initilized = False
        self.add_param = 1.0
        self.remove_param = 1.0
        self.seg_num = 0
        self.initial_frame = None
        self.thresold_sum_option = 0     #0 for L1-norm, 1 for L2-norm
        self.thresold_ratio = 3
        self.class_ratio = 1.5
        self.thresold_param = 0.5
        self.conn = sqlite3.connect('seglab.db')




    @staticmethod
    def _objectIndexVector(label_file):
        index_map = {}
        with open(label_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                index_map[row['label']] = int(row['Number'])
        return index_map

    def updateIndex(self, label_file):
        tmp_index_map = {}
        with open(label_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                tmp_index_map[int(row['label'])] = row['Number']
        self.index_map = tmp_index_map


    def _objectWeightVector(self, weight_file):
        weight_vector = np.ones(len(self.index_map))
        with open(weight_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                weight_vector[int(row['Number'])-1] = row['Weight']
        return weight_vector


    def updateWeight(self, weight_file):
        tmp_weight_vector = np.ones(len(self.index_map))
        with open(weight_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                tmp_weight_vector[int(row['Number'])-1] = row['Weight']
        self.weight_vector = tmp_weight_vector

    def objectEncodingVector(self, ann):
        tem_ojbect_vector = np.zeros(len(self.index_map))

        for item in ann:
            tem_ojbect_vector[self.index_map[item['label']]-1] += 1
        return tem_ojbect_vector

    def spatialWeightVector(self, ann):
        tmp_sw_vector = np.zeros(len(self.index_map))
        tmp_cnt_vector = np.zeros(len(self.index_map))

        for k in ann:
            if (k["xright"] - k["xleft"]) * (k["ybottom"] - k["ytop"]) < 0:
                print("error!")
            tmp_sw_vector[self.index_map[k['label']]-1] += (k["xright"] - k["xleft"]) * (k["ybottom"] - k["ytop"])
            tmp_cnt_vector[self.index_map[k['label']]-1] += 1

        return np.divide(tmp_sw_vector, tmp_cnt_vector, out=tmp_sw_vector, where=tmp_cnt_vector != 0)

    ##TODO: update this method
    def temporalWeightVector(self, ann, object_prev_vector):
        tmp_tp_vector = np.zeros(len(self.index_map))

        return np.ones(len(self.index_map))

    ##TODO: update this method
    def temporalVariationVector(self, object_prev_vector, object_cur_vector):
        tmp_tp_vector = np.zeros(len(self.index_map))

        return np.ones(len(self.index_map))


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



    ##TODO:extract more information
    def labeling(self, first, last, table):
        data_object = {"labels": [], "start": first[-1]["frameName"], "end": last[-1]["frameName"]}
        for k, v in table.items():
            data_object["labels"].append({"item": k, "frequency": v})
        data_json = json.dumps(data_object)
        print(data_json)
        return data_json


    def thresold_check(self, dm):


        if self.thresold_sum_option:
            metric_dm = np.sqrt(dm.dot(dm))/(self.thresold_ratio*pow(len(self.index_map), self.class_ratio))
        else:
            metric_dm = dm.sum()/(self.thresold_ratio*pow(len(self.index_map), self.class_ratio))

        # print(metric_dm)
        # print( math.tanh(metric_dm))

        if max(0, metric_dm) < self.thresold_param:
            return False
        else:
            return True


    def processAnnotation(self, ann_file):

        c = self.conn.cursor()

        c.execute("drop table if exists seglab")

        c.execute('''CREATE TABLE IF NOT EXISTS seglab
                     (Start TEXT, Frame TEXT, Date DATE, Run TEXT, Scene TEXT, Class TEXT, Label TEXT, Prob REAL, Location REAL, 
                     PRIMARY KEY(Start, Frame, Class, Label))''')

        curr = []
        for line in open(ann_file, 'r'):
            curr.append(json.loads(line))

        curr_list = []
        for ann in curr:
            temp = []
            frameName = ann['frameName']
            for k in ann["annotations"]:
                temp.append({"label": ''.join([i for i in k["label"] if not i.isdigit()]), "ytop": k["ytop"],
                             "ybottom": k["ybottom"], "xleft": k["xleft"], "xright": k["xright"], "prob": k["prob"],
                             "frameName": frameName})
            curr_list.append(temp)

        frame_list = []
        last_frame = []
        frame_table = None
        if not self.initilized:

            self.initial_frame = curr_list[0]
            last_frame = self.initial_frame

            frame_table = Counter()
            entries = []
            for item in self.initial_frame:
                frame_table[item['label']] += 1
                # print(self.initial_frame[0]['frameName'], item['frameName'], item['label'],str(frame_table[item['label']]))
                temp_entry = (self.initial_frame[0]['frameName'], item['frameName'], None, None, None, item['label'], str(frame_table[item['label']]), item['prob'], None)
                entries.append(temp_entry)

            c.executemany('INSERT INTO seglab VALUES (?,?,?,?,?,?,?,?,?)', entries)

            self.object_prev_vector = self.objectEncodingVector(self.initial_frame)
            self.spatial_prev_vector = self.spatialWeightVector(self.initial_frame)
            self.temporal_prev_vector = self.temporalWeightVector(self.initial_frame, self.object_prev_vector)
            self.initilized = True

            for curr_frame in curr_list[1:]:

                ann_table = Counter()
                entries = []
                for item in curr_frame:
                    ann_table[item['label']] += 1
                    print(ann_table)
                    print(ann_table["book"])
                    print(self.initial_frame[0]['frameName'], item['frameName'], item['label'], str(ann_table[item['label']]))
                    temp_entry = (self.initial_frame[0]['frameName'], item['frameName'], None, None, None, item['label'], str(ann_table[item['label']]), item['prob'], None)
                    entries.append(temp_entry)


                c.executemany('INSERT INTO seglab VALUES (?,?,?,?,?,?,?,?,?)', entries)

                tmp_prev_object = self.object_prev_vector
                tmp_spatial = self.spatial_prev_vector
                tmp_temporal = self.temporal_prev_vector
                self.object_prev_vector = self.objectEncodingVector(curr_frame)
                self.spatial_prev_vector = self.spatialWeightVector(curr_frame)
                self.temporal_prev_vector = self.temporalWeightVector(curr_frame, self.object_prev_vector)
                self.object_var_vector = self.objectVariationVector(tmp_prev_object, self.object_prev_vector)
                self.temporal_var_vector = self.temporalVariationVector(tmp_temporal, self.temporal_prev_vector)
                self.spatial_prev_vector = self.spatialWeightVector(curr_frame)

                ##detect scene change
                if self.thresold_check(self.dissimiliarityVector(self.object_var_vector, tmp_prev_object, self.temporal_var_vector, tmp_spatial, tmp_temporal, self.spatial_prev_vector)):
                    frame_list.append(self.labeling(self.initial_frame, last_frame, frame_table))
                    # seg_name = prefix + str(seq_num)
                    self.seg_num += 1
                    self.initial_frame = curr_frame
                    frame_table = ann_table

                last_frame = curr_frame

        else:
            for curr_frame in curr_list:

                ann_table = Counter()
                entries = []
                for item in curr_frame:
                    ann_table[item['label']] += 1
                    temp_entry = (self.initial_frame[0]['frameName'], item['frameName'], None, None, None, item['label'], str(ann_table[item['label']]), item['prob'], None)
                    entries.append(temp_entry)

                c.executemany('INSERT INTO seglab VALUES (?,?,?,?,?,?,?,?,?)', entries)

                tmp_prev_object = self.object_prev_vector
                tmp_spatial = self.spatial_prev_vector
                tmp_temporal = self.temporal_prev_vector
                self.object_prev_vector = self.objectEncodingVector(curr_frame)
                self.spatial_prev_vector = self.spatialWeightVector(curr_frame)
                self.temporal_prev_vector = self.temporalWeightVector(curr_frame, self.object_prev_vector)
                self.object_var_vector = self.objectVariationVector(tmp_prev_object, self.object_prev_vector)
                self.temporal_var_vector = self.temporalVariationVector(tmp_temporal, self.temporal_prev_vector)
                self.spatial_prev_vector = self.spatialWeightVector(curr_frame)

                ##detect scene change
                if self.thresold_check(self.dissimiliarityVector(self.object_var_vector, tmp_prev_object, self.temporal_var_vector, tmp_spatial, tmp_temporal, self.spatial_prev_vector)):
                    frame_list.append(self.labeling(self.initial_frame, last_frame, frame_table))
                    # seg_name = prefix + str(seq_num)
                    self.seg_num += 1
                    self.initial_frame = curr_frame
                    frame_table = ann_table

                last_frame = curr_frame

        # c.close()
        self.conn.commit()
        return json.dumps(frame_list)


    def updateDB(self):
        pass

    def resultFigure(self):
        pass

    def sceneDetection(self, ann):
        return self.processAnnotation(ann)

