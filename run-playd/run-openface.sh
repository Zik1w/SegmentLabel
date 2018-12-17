#!/bin/bash

#python seglab_stream_consumer.py -f /eb/proto/test/ml_processing/openface
python playdetect_stream_consumer.py -f /eb/proto/test/ml_processing/openface &> playd-openface.out
