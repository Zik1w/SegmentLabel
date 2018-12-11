from SegmentLabel import SegmentLabel


def main():
    seglab = SegmentLabel("config/object_label.csv", "config/object_weight.csv")
    seglab.processAnnotation("data/matrix.json")

    c = seglab.conn.cursor()

    for row in c.execute('SELECT * FROM seglab ORDER BY start'):
        print(row)

    c.close()
    seglab.conn.close()

if __name__ == '__main__':
    main()