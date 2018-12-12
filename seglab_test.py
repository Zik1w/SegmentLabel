from SegmentLabel import SegmentLabel
import json


def main():
    seglab = SegmentLabel("config/object_label.csv", "config/object_weight.csv")

    curr = []
    for line in open("data/yolo.filtered"):
        curr.append(json.loads(line))

    for ann in curr:
        # for item in ann["annotations"]:
        #     print(item["label"])
        seglab.processAnnotation(ann)

    c = seglab.conn.cursor()

    # for row in c.execute('SELECT * FROM seglab ORDER BY start'):
    #     print(row)

    c.close()
    seglab.conn.close()

if __name__ == '__main__':
    main()