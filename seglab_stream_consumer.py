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

def main(index_f, weight_f):
    # The default Face will connect using a Unix socket, or to "localhost".
    sl = SegmentLabel(index_f, weight_f)

    face = Face()
    keyChain = KeyChain()
    face.setCommandSigningInfo(keyChain, keyChain.getDefaultCertificateName())

    stream_annConsumer = Namespace("/ndn/eb/stream/run/28/annotations")
    # stream_annConsumer = Namespace('/eb/proto/test/ml_processing/yolo')
    stream_annConsumer.setFace(face)

    stream_segProducer = Namespace("/eb/proto/test/ml_processing/yolo/seglab", keyChain)
    publish_handler = GeneralizedObjectStreamHandler()
    stream_segProducer.setHandler(publish_handler)

    stream_segProducer.setFace(face,
        lambda prefixName: dump("Register failed for prefix", prefixName),
        lambda prefixName, whatever: dump("Register success for prefix", prefixName))

    def onNewAnnotation(sequenceNumber, contentMetaInfo, objectNamespace):

        ann = json.loads(str(objectNamespace.obj))

        # print(ann)

        if not "error" in ann:
            segment_result = sl.sceneDetection(ann)
            # print(segment_result)
            if segment_result and len(segment_result) > 0:
                dump("Got generalized object, sequenceNumber", sequenceNumber,
                     ", content-type", contentMetaInfo.getContentType(), ":",
                     str(time.time()))

                # dump(time.time(), "Publish scene HERE")
                # dump(time.time(), "publishing scene (segment)",
                #     publish_handler.getProducedSequenceNumber() + 1)
                publish_handler.addObject(
                    Blob(segment_result),
                    "application/json")
                print("PUBLISHED")

        # ann = json.loads(str(objectNamespace.obj))
        # print(ann)
        #
        # if not ann["error"]:
        #     segment_result = sl.sceneDetection(ann)
        #     dump("Got generalized object, sequenceNumber", sequenceNumber,
        #           ", content-type", contentMetaInfo.getContentType(), ":",
        #           str(segment_result))

    pipelineSize = 10
    stream_annConsumer.setHandler(
      GeneralizedObjectStreamHandler(pipelineSize, onNewAnnotation)).objectNeeded()

    while True:
        face.processEvents()
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
        main()

    except:
        traceback.print_exc(file=sys.stdout)
        print("Error parsing command line arguments")
        sys.exit(1)