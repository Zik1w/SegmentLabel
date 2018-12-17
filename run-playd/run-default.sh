#!/bin/bash

#python seglab_stream_consumer.py -f /eb/proto/test/ml_processing/yolo_default &> seglab-default.out
python playdetect_stream_consumer.py -f /eb/proto/test/ml_processing/yolo_default &> playd-default.out
