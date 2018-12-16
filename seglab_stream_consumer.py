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

import traceback
import sys
import time
import json
import argparse


from SegmentLabel import SegmentLabel
from pyndn import Face
from pycnl import Namespace
from pycnl.generalized_object import GeneralizedObjectStreamHandler
from pyndn.util import Blob
from pyndn.security import KeyChain, SafeBag



def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

def main(index_f, weight_f, config_f, consumerMode):
    # The default Face will connect using a Unix socket, or to "localhost".
    sl = SegmentLabel(index_f, weight_f)

    if config_f != "":
        sl.readConfig(config_f)


    face = Face()
    keyChain = KeyChain()
    face.setCommandSigningInfo(keyChain, keyChain.getDefaultCertificateName())

    stream_annConsumer_test = Namespace("/ndn/eb/stream/run/28/annotations")
    stream_annConsumer_test.setFace(face)


    if consumerMode == 'default':
        stream_annConsumer_default = Namespace('/eb/proto/test/ml_processing/yolo_default')
        stream_annConsumer_default.setFace(face)

    stream_annConsumer_show = Namespace('/eb/proto/test/ml_processing/yolo')
    stream_annConsumer_show.setFace(face)

    stream_segProducer = Namespace("/eb/proto/test/ml_processing/yolo/seglab", keyChain)
    publish_handler = GeneralizedObjectStreamHandler()
    stream_segProducer.setHandler(publish_handler)

    stream_segProducer.setFace(face,
        lambda prefixName: dump("Register failed for prefix", prefixName),
        lambda prefixName, whatever: dump("Register success for prefix", prefixName))

    def onNewAnnotation(sequenceNumber, contentMetaInfo, objectNamespace):
        ann = str(objectNamespace.obj)

        print(ann)

        if not "error" in ann:
            jsonAnn = json.loads(ann)
            # print(jsonAnn["frameName"])
            segment_result = sl.sceneDetection(jsonAnn)
            if segment_result and len(segment_result) > 0:
                dump("Got generalized object, sequenceNumber", sequenceNumber,
                     ", content-type", contentMetaInfo.getContentType(), ":",
                     str(jsonAnn["frameName"]), 'at', str(time.time()))

                # dump(time.time(), "Publish scene HERE")
                # dump(time.time(), "publishing scene (segment)",
                #     publish_handler.getProducedSequenceNumber() + 1)
                publish_handler.addObject(
                    Blob(segment_result),
                    "application/json")
                print("PUBLISHED")

    pipelineSize = 10

    if consumerMode == 'default':
        stream_annConsumer_default.setHandler(
          GeneralizedObjectStreamHandler(pipelineSize, onNewAnnotation)).objectNeeded()


    stream_annConsumer_show.setHandler(
      GeneralizedObjectStreamHandler(pipelineSize, onNewAnnotation)).objectNeeded()

    stream_annConsumer_test.setHandler(
        GeneralizedObjectStreamHandler(pipelineSize, onNewAnnotation)).objectNeeded()

    while True:
        face.processEvents()
        # We need to sleep for a few milliseconds so we don't use 100% of the CPU.
        time.sleep(0.01)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse command line args for ndn consumer and segment algorithm')
    parser.add_argument("-i", "--object index", dest='indexFile', nargs='?', const=1, type=str, default="config/object_label.csv", help='object index file')
    parser.add_argument("-w", "--object weights", dest='weightFile', nargs='?', const=1, type=str, default="config/object_weight.csv", help='object weight file')
    parser.add_argument("-c", "--algorithm config", dest="configureFile", nargs='?', const=1, type=str, default="", help='algorithm configuraiton file')
    parser.add_argument("-m", "--running mode", dest='mode', nargs='?', const=1, type=str, default="", help='the mode for fetching data')


    args = parser.parse_args()

    try:
        main(args.indexFile, args.weightFile, args.configureFile, args.mode)

    except:
        traceback.print_exc(file=sys.stdout)
        print("Error parsing command line arguments")
        sys.exit(1)