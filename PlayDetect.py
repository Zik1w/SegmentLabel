from pymongo import MongoClient
from collections import Counter
import json
import csv
import sqlite3


class PlayDetect(object):
    def __init__(self, label_file, weight_file, config_file=None):
        self.index_map = self._objectIndexVector(label_file)
        self.weight_vector = self._objectWeightVector(weight_file)
        self.live_frame = None
        self.historical_seg = []
        self.frame_table = []
        self.top_table = Counter()
        self.compareSegConn = sqlite3.connect('seglab.db')
        self.resultSegConn = sqlite3.connect('playdetect.db')

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
        seg.append(len(self.historical_seg)+1)
        self.historical_seg.append(seg)

    def processLiveFrame(self, live_frame):
        self.live_frame = live_frame
        ann = self.live_frame["annotations"]
        for item in ann:
            # self.frame_table[item['label']] += self.weight_vector[self.index_map[item['label']]]
            self.frame_table[item['label']] += 1

    def segComparsion(self, seg):
        weighted_similarity = 0
        for k in seg["info"]:
            weighted_similarity += max((k["frequency"], self.frame_table[k["label"]]))

        return weighted_similarity

    def pickTops(self, live_frame):
        self.processLiveFrame(live_frame)
        self.top_table = Counter()
        for s in self.historical_seg:
            self.top_table[s[-1]] = self.segComparsion(s)

        return self.top_table.most_common(k)

    def sort(self):
        pass

    def storeToDatabase(self, segName, segInfo):
        c = self.resultSegConn.cursor()

        c.execute("drop table if exists resultseg")

        c.execute('''CREATE TABLE IF NOT EXISTS seglab
                     (SceneSegName TEXT, StartFrame TEXT, EndFrame, TEXT Date DATE, Run TEXT, Scene TEXT, Info TEXT, 
                     PRIMARY KEY(SceneSegName))''')

        resultseg_entry = (segName, segInfo['start'], segInfo['end'], None, None, None, segInfo['info'])

        c.execute('INSERT INTO resultseg VALUES (?,?,?,?,?,?,?)', resultseg_entry)

        c.close()



# def main():
#     ###set up database
#     client = MongoClient('localhost', 27017)
#
#     db = client['segment-database']
#
#     ##readin feature weights
#     weight_vector = {}
#     with open('config/object_weight.csv', newline='') as csvfile:
#         reader3 = csv.DictReader(csvfile)
#
#         for row in reader3:
#             weight_vector[row['label']] = row['Weight']
#
#     jsonString = "data/matrix.json"
#     curr = []
#     for line in open(jsonString, 'r'):
#         curr.append(json.loads(line))
#
#     curr_list = []
#     for ann in curr:
#         temp = []
#         frameName = ann['frameName']
#         # print(frameName)
#         for k in ann["annotations"]:
#             # temp.append({"label": ''.join([i for i in k["label"] if not i.isdigit()]), "prob": k["prob"]})
#             temp.append({"label": ''.join([i for i in k["label"] if not i.isdigit()]), "ytop": k["ytop"],
#                          "ybottom": k["ybottom"], "xleft": k["xleft"], "xright": k["xright"], "prob": k["prob"],
#                          "frameName": frameName})
#         curr_list.append(temp)
#
#
#     initial_frame = curr_list[0]
#     last_frame = curr_list[-1]
#
#     cnt = 0
#     frame_table = Counter()
#     frame_weight = 0
#     for item in initial_frame:
#         tmp_weight = weight_vector[item['label']]
#         frame_weight += tmp_weight
#         frame_table[item['label']] += tmp_weight
#
#
#     # last_table = Counter()
#     # last_weight = 0
#     # for item in last_frame:
#     #     tmp_weight = weight_vector[item['label']]
#     #     last_weight += tmp_weight
#     #     last_table[item['label']] += tmp_weight
#
#     #####L1 NORM
#     x = 0.5
#     y = 0.5
#     bound = 0.5
#     # weights = (x*initial_weight+y*last_weight)
#     weights = frame_weight
#     low_weight = weights * (1 - bound)
#     high_weight = weights * (1 + bound)
#
#
#     ####EXECUTE QUERY
#     weight_query = { "weights": { "$gt": low_weight, "lt": high_weight } }
#
#     similar_frames = db.bios.find(weight_query)
#     index_frames = range(len(similar_frames))
#
#     top_seg = 10
#
#     #####SORT and FIND TOP K Segments
#     sort_table = Counter()
#     cnt = 0
#     for item in similar_frames:
#         sort_table[str(cnt)] = item["weights"] - weights
#         cnt +=1
#
#     top_frames = sort_table.most_common(top_seg)
#
#     sorted_similar_frames = []
#
#     for kv in sort_table.most_common(top_seg).keys():
#         sorted_similar_frames.append(similar_frames[int(kv)])
#
#     # db.bios.find(
#     #     {start_weight:
#     #         { $gt: value1, $lt: value2}
#     #
#     #     },
#     #
#     #     {start_weight:
#     #         { $gt: value1, $lt: value2}
#     #
#     #     },
#     # );
#
#     return sorted_similar_frames