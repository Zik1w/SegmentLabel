from pymongo import MongoClient
from collections import Counter
import json


def main():
    ###set up database
    client = MongoClient('localhost', 27017)

    db = client['segment-database']

    ##readin feature weights
    weight_vector = {}
    with open('config/object_weight.csv', newline='') as csvfile:
        reader3 = csv.DictReader(csvfile)

        for row in reader3:
            weight_vector[row['label']] = row['Weight']

    jsonString = "data/matrix.json"
    curr = []
    for line in open(jsonString, 'r'):
        curr.append(json.loads(line))

    curr_list = []
    for ann in curr:
        temp = []
        frameName = ann['frameName']
        # print(frameName)
        for k in ann["annotations"]:
            # temp.append({"label": ''.join([i for i in k["label"] if not i.isdigit()]), "prob": k["prob"]})
            temp.append({"label": ''.join([i for i in k["label"] if not i.isdigit()]), "ytop": k["ytop"],
                         "ybottom": k["ybottom"], "xleft": k["xleft"], "xright": k["xright"], "prob": k["prob"],
                         "frameName": frameName})
        curr_list.append(temp)


    initial_frame = curr_list[0]
    last_frame = curr_list[-1]

    cnt = 0
    inital_table = Counter()
    initial_weight = 0
    for item in initial_frame:
        tmp_weight = weight_vector[item['label']]
        initial_weight += tmp_weight
        inital_table[item['label']] += tmp_weight


    last_table = Counter()
    last_weight = 0
    for item in last_frame:
        tmp_weight = weight_vector[item['label']]
        last_weight += tmp_weight
        last_table[item['label']] += tmp_weight

    #####L1 NORM
    x = 0.5
    y = 0.5
    bound = 0.5
    weights = (x*initial_weight+y*last_weight)
    low_weight = weights * (1 - bound)
    high_weight = weights * (1 + bound)


    ####EXECUTE QUERY
    weight_query = { "weights": { "$gt": low_weight, "lt": high_weight } }

    similar_frames = db.bios.find(weight_query)
    index_frames = range(len(similar_frames))

    top_seg = 10

    #####SORT and FIND TOP K Segments
    sort_table = Counter()
    cnt = 0
    for item in similar_frames:
        sort_table[str(cnt)] = item["weights"] - weights
        cnt +=1

    top_frames = sort_table.most_common(top_seg)

    sorted_similar_frames = []

    for kv in sort_table.most_common(top_seg).keys():
        sorted_similar_frames.append(similar_frames[int(kv)])

    # db.bios.find(
    #     {start_weight:
    #         { $gt: value1, $lt: value2}
    #
    #     },
    #
    #     {start_weight:
    #         { $gt: value1, $lt: value2}
    #
    #     },
    # );

    return sorted_similar_frames

    client.close()


if __name__ == '__main__':
    main()