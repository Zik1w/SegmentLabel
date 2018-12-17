#!/bin/bash

#python seglab_stream_consumer.py -f /eb/proto/test/ml_processing/yolo
python playdetect_stream_consumer.py -f /eb/proto/test/ml_processing/yolo &> playd-show.out
