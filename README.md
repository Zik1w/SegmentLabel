# SegmentLabel
segment labeling module

## Files
SegmentLabel.py: Class file for segment labeling module 
PlayDetect.py: Class file for play detect module
seglab_test.py: standalone test for scene segment algorithm

## Work Flow
- Initialize the publisher of annotataion in the server[prefix:'/eb/proto/test/ml_processing/yolo'] OR run the simulation anno_publisher.py [prefix:"/ndn/eb/stream/run/28/annotations"]
- Change the seglab_stream_consumer.py file accordingly with corresponding prefix from the annotation publisher, default is the server one
- Run the playdetect_stream_consumer.py, 
 - It fetch scene segment json string that produced by seglab_stream_consumer.py and store the scene segment
 - It also fetches the new annotation for the live frame and query the database to retrieve most similar scene [prefix:'/eb/proto/test/ml_processing/yolo']



## Configurability
- seglab_stream_consumer.py can read three Command line arguments for configuration files, all configuration file should be stored in config subdirectory.

  seglab_stream_consumer.py --[location of label index file] --[location of weight file] --[custermized parameters file]
- playdetect_stream_consumer.py can read three Command line arguments for configuration files, all configuration file should be stored in config subdirectory.
  playdetect_stream_consumer.py --[location of label index file] --[location of weight file] --[custermized parameters file]

  

