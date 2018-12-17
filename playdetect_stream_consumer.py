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

from PlayDetect import PlayDetect
from pyndn.util import Blob
from pyndn import Face, Name
from pycnl import Namespace
from pycnl.generalized_object import GeneralizedObjectStreamHandler
from pyndn.security import KeyChain


def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

def main(index_f, weight_f, consumerMode, k, fetchPrefix, publishPrefix):
    # The default Face will connect using a Unix socket, or to "localhost".
    pd = PlayDetect(index_f, weight_f, k)

    face = Face()
    keyChain = KeyChain()
    face.setCommandSigningInfo(keyChain, keyChain.getDefaultCertificateName())

    # sceneConsumer = Namespace("/ndn/eb/stream/run/28/annotation")
    engine = str(Name(fetchPrefix)[-1])
    sceneFetchPrefix = Name('/eb/seglab').append(engine)

    print(' > Will fetch annotations from '+fetchPrefix)
    print(' > Will fetch scenes from '+sceneFetchPrefix.toUri())

    sceneConsumer = Namespace(sceneFetchPrefix)
    sceneConsumer.setFace(face)

    annotationsConsumer = Namespace(fetchPrefix)

    #if consumerMode == "test":
    #    annotationsConsumer = Namespace("/ndn/eb/stream/run/28/annotations")
    #elif consumerMode == "default":
    #    annotationsConsumer = Namespace('/eb/proto/test/ml_processing/yolo_default')

    annotationsConsumer.setFace(face)

    playdetectProducer = Namespace(Name(publishPrefix).append(engine))
    print(' > Will publish playdetect data under '+playdetectProducer.getName().toUri())

    playdSegmentsHandler = GeneralizedObjectStreamHandler()
    # TODO: set freshness to 0
    playdetectProducer.setHandler(playdSegmentsHandler)

    playdetectProducer.setFace(face,
      lambda prefixName: dump("Register failed for prefix", prefixName),
      lambda prefixName, whatever: dump("Register success for prefix", prefixName))

    def onNewScene(sequenceNumber, contentMetaInfo, objectNamespace):
        dump("Got scene (segment) :", str(objectNamespace.obj))

        if str(objectNamespace.obj):
            # TBD
            # Store scene segment AND scene segment NAME into a database
            sceneSegmentName = objectNamespace.getName()
            sceneSegment = json.loads(str(objectNamespace.obj))
            pd.storeToDatabase(sceneSegmentName, sceneSegment)

    def onNewAnnotation(sequenceNumber, contentMetaInfo, objectNamespace):
        # dump("Got new annotation:", str(objectNamespace.obj))
        stringObj = str(objectNamespace.obj)
        if stringObj:
            # TBD
            # query interval configurable
            itIsTimeToQueryDatabase = True
            if itIsTimeToQueryDatabase:
                # TBD
                # run query against the databse, using recevied annotation
                # the result should be a list that contains scene segment names (see above)
                # FOR NOW: let's have startFrame end endFrame in the results
                # most likely -- parameterize query, i.e. give argument maxResultNum
                result = pd.pickTops(json.loads(stringObj), k)
                if result:
                    playdSegmentsHandler.addObject(
                        Blob(json.dumps(result)),
                        "application/json")

    pipelineSize = 10
    sceneConsumer.setHandler(
        GeneralizedObjectStreamHandler(pipelineSize, onNewScene)).objectNeeded()

    annotationsConsumer.setHandler(
        GeneralizedObjectStreamHandler(pipelineSize, onNewAnnotation)).objectNeeded()

    while True:
        face.processEvents()
        # We need to sleep for a few milliseconds so we don't use 100% of the CPU.
        time.sleep(0.01)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse command line args for ndn consumer and segment algorithm')
    parser.add_argument("-i", "--object index", dest='indexFile', nargs='?', const=1, type=str, default="config/object_label.csv", help='object index file')
    parser.add_argument("-w", "--object weights", dest='weightFile', nargs='?', const=1, type=str, default="config/object_weight.csv", help='object weight file')
    parser.add_argument("-k", "--top k results", dest='topNumResult', nargs='?', const=1, type=int, default=10, help='object weight file')
    parser.add_argument("-m", "--running mode", dest='mode', nargs='?', const=1, type=str, default="", help='the mode for fetching data')
    parser.add_argument("-f", "--fetch", dest='fetch', nargs='?', const=1, type=str, default="", help='prefix for fetching data')
    parser.add_argument("-p", "--publish", dest='publish', nargs='?', const=1, type=str, default="/eb/playdetect/segments", help='prefix for publishing segments')

    args = parser.parse_args()

    try:
        main(args.indexFile, args.weightFile, args.mode, args.topNumResult, args.fetch, args.publish)

    except:
        traceback.print_exc(file=sys.stdout)
        print("Error parsing command line arguments")
        sys.exit(1)
