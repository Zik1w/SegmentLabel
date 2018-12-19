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
from pyndn import Face, Name
from pycnl import Namespace
from pycnl.generalized_object import GeneralizedObjectStreamHandler
from pyndn.util import Blob
from pyndn.security import KeyChain, SafeBag



def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

def main(index_f, weight_f, config_f, consumerMode, th, fetchPrefix, publishPrefix):
    # The default Face will connect using a Unix socket, or to "localhost".
    instance_prefix = fetchPrefix.split("/")[-1]
    sl = SegmentLabel(index_f, weight_f, instance_prefix, th)

    if config_f != "":
        sl.readConfig(config_f)


    face = Face()
    keyChain = KeyChain()
    face.setCommandSigningInfo(keyChain, keyChain.getDefaultCertificateName())

    #stream_annConsumer_test = Namespace("/ndn/eb/stream/run/28/annotations")
    #stream_annConsumer_test.setFace(face)
    print(' > Will fetch from '+str(fetchPrefix))
    stream_annConsumer_show = Namespace(fetchPrefix)
    stream_annConsumer_show.setFace(face)

    log_f = open(str("seglab_log") + ".txt", "w")
    log_f.close()


    stream_segProducer = Namespace(Name(publishPrefix).append(Name(fetchPrefix)[-1]), keyChain)
    print(' > Will publish segments under '+str(stream_segProducer.getName()))
    publish_handler = GeneralizedObjectStreamHandler()
    # publish_handler.setLatestPacketFreshnessPeriod(30)
    stream_segProducer.setHandler(publish_handler)

    stream_segProducer.setFace(face,
        lambda prefixName: dump("Register failed for prefix", prefixName),
        lambda prefixName, whatever: dump("Register success for prefix", prefixName))

    def onNewAnnotation(sequenceNumber, contentMetaInfo, objectNamespace):
        ann = str(objectNamespace.obj)
        segment_result = []

        jsonAnn = json.loads(ann)
        # print(jsonAnn["frameName"])

        if not "error" in ann:
            jsonAnn = json.loads(ann)
            # print(jsonAnn["frameName"])
            segment_result = sl.sceneDetection(jsonAnn)
            if segment_result and len(segment_result) > 0:
                print(segment_result)
                #dump("Got generalized object, sequenceNumber", sequenceNumber,
                #     ", content-type", contentMetaInfo.getContentType(), ":",
                #     str(jsonAnn["frameName"]), 'at', str(time.time()))

                publish_handler.addObject(
                    Blob(json.dumps(segment_result)),
                    "application/json")
                print(" > PUBLISHED SCENE "+str(publish_handler.getProducedSequenceNumber()))


                # # logging the result
                # if segment_result:
                with open(str("seglab_log") + ".txt", "w+") as f:
                    f.write("PUBLISHED SCENE: %s" % str(publish_handler.getProducedSequenceNumber()))
                    f.write("%s\r\n" % segment_result)

    pipelineSize = 0

    #if consumerMode == 'default':
    #    stream_annConsumer_default.setHandler(
    #      GeneralizedObjectStreamHandler(pipelineSize, onNewAnnotation)).objectNeeded()


    stream_annConsumer_show.setHandler(
      GeneralizedObjectStreamHandler(pipelineSize, onNewAnnotation)).objectNeeded()

    #stream_annConsumer_test.setHandler(
    #    GeneralizedObjectStreamHandler(pipelineSize, onNewAnnotation)).objectNeeded()

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
    parser.add_argument("-th", "--threshold", dest='threshold', nargs='?', const=1, type=float, default=0.4, help='adjust threshold of scene change')
    parser.add_argument("-f", "--fetch", dest='fetch', nargs='?', const=1, type=str, default="", help='prefix for fetching data')
    parser.add_argument("-p", "--publish", dest='publish', nargs='?', const=1, type=str, default="/eb/seglab", help='prefix for publishing segments')

    args = parser.parse_args()

    try:
        main(args.indexFile, args.weightFile, args.configureFile, args.threshold, args.mode, args.fetch, args.publish)

    except:
        traceback.print_exc(file=sys.stdout)
        print("Error parsing command line arguments")
        sys.exit(1)