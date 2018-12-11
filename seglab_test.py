from SegmentLabel import SegmentLabel


def main():
    seglab = SegmentLabel("config/object_label.csv", "config/object_weight.csv")
    seglab.processAnnotation("data/yolo.filtered")

if __name__ == '__main__':
    main()