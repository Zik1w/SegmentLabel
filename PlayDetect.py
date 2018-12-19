from collections import Counter
import json
import csv
import sqlite3
import numpy as np
from pyndn.util.common import Common

class PlayDetect(object):
    def __init__(self, label_file, weight_file, instance_prefix=None, topNumber=10, query_interval=1):
        self.index_map = self._objectIndexVector(label_file)
        self.weight_vector = self._objectWeightVector(weight_file)
        self.live_frame = None
        self.historical_seg = []
        self.frame_table = Counter()
        self.top_table = Counter()
        self.topNumber = topNumber
        self.previousPublishMs = Common.getNowMilliseconds()
        self.publishIntervalMs = 1000.0 * query_interval
        self.tmp_top_table = {}

        if instance_prefix:
            self.resultSegConn = sqlite3.connect('playdetect_' + str(instance_prefix) + '.db')
        else:
            self.resultSegConn = sqlite3.connect('playdetect.db')

        c_init = self.resultSegConn.cursor()

        c_init.execute("drop table if exists segResult")

        c_init.execute("drop table if exists segInfo")

        c_init.execute('''CREATE TABLE IF NOT EXISTS segResult
                     (SceneName TEXT, StartFrame TEXT, EndFrame, TEXT Date DATE, Run TEXT, Scene TEXT, Summary TEXT,
                     PRIMARY KEY(SceneName))''')

        #c_init.execute('''CREATE TABLE IF NOT EXISTS segInfo
        #             (Start TEXT, Frame TEXT, Date DATE, Run TEXT, Scene TEXT, Class TEXT, Label TEXT, Prob REAL, Location REAL,
        #             PRIMARY KEY(Start, Frame, Class, Label))''')

        c_init.execute('''CREATE TABLE IF NOT EXISTS segInfo
                     (SceneName TEXT, SceneInfo TEXT)''')


        c_init.close()

    @staticmethod
    def _objectIndexVector(label_file):
        index_map = {}
        with open(label_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                index_map[row['label']] = int(row['Number'])
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

    def processSeg(self, seg):
        # seg.append(len(self.historical_seg)+1)
        self.historical_seg.append(seg)

    def processLiveFrame(self, live_frame):
        self.live_frame = live_frame
        ann = self.live_frame["annotations"]
        for item in ann:
            # self.frame_table[item['label']] += self.weight_vector[self.index_map[item['label']]]
            self.frame_table[item['label']] += 1

    def segComparison(self, seg):
        weighted_similarity = 0
        for k in seg["info"]:
            # weighted_similarity += min((k["frequency"], self.frame_table[k["label"]]))
            weighted_similarity += min((k["frequency"], self.frame_table[k["label"]]))


        return weighted_similarity

    def pickTops(self, live_frame, k):
        self.topNumber = k
        self.processLiveFrame(live_frame)
        self.top_table = Counter()

        c_segQuery = self.resultSegConn.cursor()
        for s in self.historical_seg:
            #self.top_table[str(s["start"] + "_" + s["end"])] = self.segComparison(s)

            c_segQuery = self.resultSegConn.cursor()
            segQuery = []
            segQuery.append(s["start"])
            segQuery.append(s["end"])
            segName = ''
            for row in c_segQuery.execute('SELECT * FROM segResult WHERE StartFrame = ? AND EndFrame = ?', segQuery):
                segName = (row[0])

            s['SceneName'] = segName
            self.top_table[json.dumps(s)] = self.segComparison(s)
            # self.top_table[str(s)] = self.segComparison(s)


        self.tmp_top_table = {}
        for row in c_segQuery.execute('SELECT * FROM segInfo'):
            segment_str = str(row[1])
            segment = json.loads(segment_str)
            segment['SceneName'] = str(row[0])
            # print(segment)
            self.tmp_top_table[json.dumps(segment)] = self.segComparison(segment)
            pass

        c_segQuery.close()


        # top_sorted_seg=self.top_table.most_common(self.topNumber)
        # top_sorted_seg = sorted(self.top_table, key=self.top_table.get, reverse=True)[:self.topNumber]
        top_sorted_seg = sorted(self.tmp_top_table, key=self.tmp_top_table.get, reverse=True)[:self.topNumber]

        tmp_seg = []
        print("most similarity scenes are:")
        for s in top_sorted_seg:
            seg = json.loads(s)
            print(seg["info"])
            tmp_seg.append(seg)

        result_sorted_seg = {'segment': tmp_seg}

        # result_sorted_seg = d = {k: v for k, v in enumerate(top_sorted_seg)}
        return result_sorted_seg

    def sort(self):
        pass

    def storeToDatabase(self, segName, segInfo):

        self.processSeg(segInfo)
        c = self.resultSegConn.cursor()

        resultseg_entry = (str(segName), segInfo['start'], segInfo['end'], None, None, None, str(segInfo["info"]))  #replace last entry with segment information
        c.execute('INSERT INTO segResult VALUES (?,?,?,?,?,?,?)', resultseg_entry)

        resultseg_info_entry = (str(segName), json.dumps(segInfo))
        c.execute('INSERT INTO segInfo VALUES (?,?)', resultseg_info_entry)

        c.close()

        # self.compareSegConn.commit()
        self.resultSegConn.commit()
    

    def itIsTimeToQueryDatabase(self):
        now = Common.getNowMilliseconds()
        #print(now)
	    #print(self.previousPublishMs + self.publishIntervalMs)
        if now  >= self.previousPublishMs + self.publishIntervalMs:
            self.previousPublishMs = now
            return True
        else:
            return False


