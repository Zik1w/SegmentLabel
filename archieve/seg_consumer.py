# -*- Mode:python; c-file-style:"gnu"; indent-tabs-mode:nil -*- */

import sys
import time
import argparse
import traceback

from pyndn import Interest
from pyndn import Name
from pyndn import Face



class Consumer(object):

    def __init__(self, prefix):
        # Create a connection to the local forwarder and
        # initialize outstanding Interest state keeping
        self.prefix = Name('/eb/proto/test/ml_processing/yolo')
        self.outstanding = dict()
        self.isDone = False
        self.face = Face("127.0.0.1")
        self.run = 0
        self.clip = 0
        self.seq_no = 1


    def run(self):
        # Send Interest and run event loop until
        # we receive a response or exceed retry attempts.
        try:
            self._sendNextInterest(self.prefix + '/run/' + str(self.run) + '/frame-annotation/' + Name.Component.fromSequenceNumber(self.seq_no))

            while not self.isDone:
                self.face.processEvents()
                time.sleep(0.01)

        except RuntimeError as e:
            print("ERROR: %s" % e)


    def _sendNextInterest(self, name):
        # Create an Interest using the specificed run&clip number with the frame-annotation namespace and record it in our outstanding Interest.
        # Then, send the Interest out our Face.
        interest = Interest(name)
        uri_i = name.toUri()

        interest.setInterestLifetimeMilliseconds(4000)
        interest.setMustBeFresh(True)

        if uri_i not in self.outstanding:
            self.outstanding[uri_i] = 1

        self.face.expressInterest(interest, self._onData, self._onTimeout)
        print("Sent Interest for %s" % uri_i)

    def _onData(self, interest, data):
        # Print the Data's payload and remove
        # the associated Interest from the outstanding table.
        # Finally, signal the event loop that we are finished.
        annotation = data.getContent()
        name = data.getName()
        seg_annotation = segDetect()

        # print("Received data: %s" % payload.toRawStr())
        del self.outstanding[name.toUri()]

        # run the event loop forever
        # self.isDone = True

    def _onTimeout(self, interest):
        # Increment the retry count and resend the Interest
        # if we have not exceeded the maximum number of retries.
        name = interest.getName()
        uri_t = name.toUri()

        print("TIMEOUT #%d: %s" % (self.outstanding[uri_t], uri_t))
        self.outstanding[uri_t] += 1

        if self.outstanding[uri_t] <= 3:
            self._sendNextInterest(name)
        else:
            # self.isDone = True
            print("Fail to fetch data for interest: %s" % uri_t)



if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description='Parse command line args for ndn consumer')
    # parser.add_argument("-u", "--uri", required=True, help='ndn name to retrieve')
    #
    # args = parser.parse_args()

    try:
        # uri = args.uri
        Consumer("").run()

    except:
        traceback.print_exc(file=sys.stdout)
        print "Error parsing command line arguments"
        sys.exit(1)