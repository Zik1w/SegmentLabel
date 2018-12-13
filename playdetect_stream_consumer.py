# -*- Mode:python; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2018 Regents of the University of California.
# Author: Jeff Thompson <jefft0@remap.ucla.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# A copy of the GNU Lesser General Public License is in the file COPYING.

"""
This tests fetching a stream of generalized objects provided by
test_generalized_object_stream_producer (which must be running).
"""

import time
import json
import traceback
import sys
import argparse
# import PlayDetect

from pyndn import Face
from pycnl import Namespace
from pycnl.generalized_object import GeneralizedObjectStreamHandler


def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

def main(index_f, weight_f):
    # The default Face will connect using a Unix socket, or to "localhost".
    # pd = PlayDetect(index_f, weight_f)

    face_consumer = Face()
    keyChain = KeyChain()
    face_consumer.setCommandSigningInfo(keyChain, keyChain.getDefaultCertificateName())

    # stream_consumer = Namespace("/ndn/eb/stream/run/28/annotation")
    stream_consumer = Namespace('/eb/proto/test/ml_processing/yolo/seglab')
    stream_consumer.setFace(face_consumer)

    annotationsStream = Namespace('/eb/proto/test/ml_processing/yolo')
    annotationsStream.setFace(face_consumer)

    playdetectProducer = Namespace('/eb/playdetect/segments')
    playdSegmentsHandler = GeneralizedObjectStreamHandler()
    playdetectProducer.setHandler(playdSegmentsHandler)

    playdetectProducer.setFace(face_consumer,
      lambda prefixName: dump("Register failed for prefix", prefixName),
      lambda prefixName, whatever: dump("Register success for prefix", prefixName))

    def onNewObject(sequenceNumber, contentMetaInfo, objectNamespace):
        dump("Got scene (segment) :", str(objectNamespace.obj))

        if str(objectNamespace.obj):
            # TBD
            # Store scene segment AND scene segment NAME into a database
            sceneSegmentName = objectNamespace.getName()
            sceneSegment = json.loads(objectNamespace.obj)
            storeToDatabase(sceneSegment)

    def onNewAnnotation(sequenceNumber, contentMetaInfo, objectNamespace):
        dump("Got new annotation:", str(objectNamespace.obj))

        if str(objectNamespace.obj):
            # TBD
            # query interval configurable
            if itIsTimeToQueryDatabase:
                # TBD
                # run query against the databse, using recevied annotation
                # the result should be a list that contains scene segment names (see above)
                # FOR NOW: let's have startFrame end endFrame in the results
                # most likely -- parameterize query, i.e. give argument maxResultNum
                result = doQuery(str(objectNamespace.obj))
                if result is GOOD:
                    playdSegmentsHandler.addObject(
                        Blob(json.dumps(result)),
                        "application/json")


    pipelineSize = 10
    stream_consumer.setHandler(
      GeneralizedObjectStreamHandler(pipelineSize, onNewObject)).objectNeeded()

    while True:
        face_consumer.processEvents()
        # We need to sleep for a few milliseconds so we don't use 100% of the CPU.
        time.sleep(0.01)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse command line args for ndn consumer and segment algorithm')
    parser.add_argument("-i", "--object index", dest='indexFile', nargs='?', const=1, type=str, default="config/object_label.csv", help='object index file')
    parser.add_argument("-w", "--object weights", dest='weightFile', nargs='?', const=1, type=str, default="config/object_weight.csv", help='object weight file')

    args = parser.parse_args()

    try:
        index_file = args.indexFile
        weight_file = args.weightFile
        main(index_file, weight_file)

    except:
        traceback.print_exc(file=sys.stdout)
        print("Error parsing command line arguments")
        sys.exit(1)