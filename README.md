# SegmentLabel
segment labeling module

## Files
seglab_stream_consumer.py: the runnable file that run the seglab algorithm and publish scene segment if detect a change.
playdetect_stream_consumer.py: the runnable file that run the playdetect algorithm and publish most similar scenes based on a pre-defined time interval.
SegmentLabel.py: Class file for segment labeling module 
PlayDetect.py: Class file for play detect module
seglab_test.py: standalone test for scene segment algorithm

## Work Flow
- First the publisher of annotataion in the server[prefix:'/eb/proto/test/ml_processing/yolo'] OR run the simulation anno_publisher.py [prefix:"/ndn/eb/stream/run/28/annotations"]
- Run the seglab_stream_consumer.py file accordingly with corresponding prefix from the annotation publisher
    - Fetch frame annotations from the publisher
    - Publish the scene segment result
- Run the playdetect_stream_consumer.py,
    - Fetch scene segment json string that produced by seglab_stream_consumer.py and store the scene segment into corresponding sqlite database
    - Fetches the new annotation for the live frame and query the database to retrieve most similar scene [prefix:'/eb/proto/test/ml_processing/yolo']
    - Publish the similar scenes



## Configurability
- seglab_stream_consumer.py can read three Command line arguments for configuration files, all configuration file should be stored in config subdirectory.
    - seglab_stream_consumer.py -i[location of label index file] -w [location of weight file] -c [custermized parameters file] -f [custermized fetch namespace prefix] -p [custermized publish namespace prefix]
- playdetect_stream_consumer.py can read three Command line arguments for configuration files, all configuration file should be stored in config subdirectory.
    - playdetect_stream_consumer.py -i[location of label index file] -w [location of weight file] -k [Top N results] -f [custermized fetch namespace prefix] -p [custermized publish namespace prefix] -t [the publish time interval, unit in second]

  
## Seglab Configure File Parameter
- AnnoProFilter: to filter object with lower probabilities [0, 1], default 0.05
- Weight: the overall weighted parameter for the weight vector  [1, 10], default 1
- Object: the overall weighted parameter for the object vector  [1, 10], default 1
- Time(Unused): the overall weighted parameter for the temporal vector
- Size(Unused): the overall weighted parameter for the spatial vector
- Overtime(Unused): the overall weighted parameter for the temporal vector
- FrameRate(Unused): the frame rate that influence the temporal vector
- **MinSceneDuration**: the minimum time to generate a new based on received frame number [0, ], default 25
- WeightForAdd: frame weight change for adding a single object. [0, 2], default 1
- WeightForRemove: frame weight change for removing a single object. [0, 2], default 1
- Sum: boolean for 0/1 to indicate the evaluation method, , default 0
- FrequenceThreshold: how many objects with weight of value 1 needs for the scene change to happen. [1, 10], default 3
- ClassRatio: the ratio regards to the total number of object classes. [0.01, 0.1], default 0.01
- **Threshold**: a threshold probability to determine if the frame is in the same frame, lower than means same scene. [0,1], default 0.4