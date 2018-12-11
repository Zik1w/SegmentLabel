# -*- Mode:python; c-file-style:"gnu"; indent-tabs-mode:nil -*- */

import sys
import time
import argparse
import traceback
import random

from pyndn import Name
from pyndn import Data
from pyndn import Face
from pyndn.security import KeyChain


class Producer(object):

    def __init__(self):
        # Initialize our keychain
        self.keyChain = KeyChain()
        self.isDone = False
        self.namesp = '/ndn/eb/'

    def run(self):
        # Create a connection to the local forwarder.
        face = Face()

        prefix = Name(namesp)
        # Use the system default key chain and certificate name to sign commands.
        face.setCommandSigningInfo(self.keyChain, self.keyChain.getDefaultCertificateName())
        # Also use the default certificate name to sign Data packets.
        face.registerPrefix(prefix, self.onInterest, self.onRegisterFailed)

        print("Registering prefix: %s" % prefix.toUri())

        # Run the event loop forever. Use a short sleep to
        # prevent the Producer from using 100% of the CPU.
        while not self.isDone:
            face.processEvents()
            time.sleep(0.01)

    def onInterest(self, prefix, interest, transport, registeredPrefixId):
        # Create a response Data packet based on the type of incoming interest
        # Then, sign the Data with our keychain and send it out
        # using transport.
        interestName = interest.getName()

        if interestName.split('/')[:-1] == 'ndnrtc' :
            if segDect().newSegDetected():
                data = Data(segLabName + '/segment/' + segDect().newSeg().label)
                # set the palyload with the new segment
                data.setContent(segDect().newSeg().ann)

                # set refresh period
                # hourMilliseconds = 3600 * 1000
                # data.getMetaInfo().setFreshnessPeriod(hourMilliseconds)

                # manually adjust the FreshnessPeriod based on the time of producing a data packet
                productionTimeGap = 100 * 1000
                data.getMetaInfo().setFreshnessPeriod(productionTimeGap)

                # sign the packet
                self.keyChain.sign(data, self.keyChain.getDefaultCertificateName())

                transport.send(data.wireEncode().toBuffer())
                data.setContent(segDect().newSeg())
            else:
                print("no new segment detected at: %s" % interestName.toUri())
            print("Replied to: %s" % interestName.toUri())
        elif interestName.split('/')[:-1] == 'frame-annotation':
            if segDect().newSegDetected():
                data = Data(segLabName + '/segment/' + segDect().newSeg()['seglab'])
                # set the palyload with the new segment
                data.setContent(segDect().newSeg())

                # set refresh period
                hourMilliseconds = 3600 * 1000
                data.getMetaInfo().setFreshnessPeriod(hourMilliseconds)

                # sign the packet
                self.keyChain.sign(data, self.keyChain.getDefaultCertificateName())

                transport.send(data.wireEncode().toBuffer())
                data.setContent(segDect().newSeg())
            else:
                print("no new segment detected at: %s" % interestName.toUri())
            print("Replied to: %s" % interestName.toUri())

        #send historical similar segment to the playdetect engine
        elif interestName.split('/')[:-3] == 'cue':
            pre_seg = segDect().similarHistory(interestName.split('/')[:-1])
            data = Data(segLabName + '/segment/' + pre_seg['seglab'])
            data.setContent(pre_seg)

            # set refresh period
            hourMilliseconds = 3600 * 1000
            data.getMetaInfo().setFreshnessPeriod(hourMilliseconds)

            # sign the packet
            self.keyChain.sign(data, self.keyChain.getDefaultCertificateName())

            transport.send(data.wireEncode().toBuffer())
            data.setContent(segDect().newSeg())
            print("Replied to: %s" % interestName.toUri())
        else:
            print("Replied to: %s" % interestName.toUri())
            pass



    def onRegisterFailed(self, prefix):
        # Print an error message and signal the event loop to terminate
        print("Register failed for prefix: %s" % prefix.toUri())
        self.isDone = True



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse command line args for ndn producer')
    parser.add_argument("-n", "--namespace", required=True, help='namespace to listen under')

    args = parser.parse_args()

    try:
        # namespace = args.namespace
        # Producer().run(namespace)
        Producer().run()
    except:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)