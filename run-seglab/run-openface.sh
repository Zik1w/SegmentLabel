#!/bin/bash

python ../seglab_stream_consumer.py -i `pwd`/../config/object_label.csv -w `pwd`/../config/object_weight.csv -f /eb/proto/test/ml_processing/openface2 

