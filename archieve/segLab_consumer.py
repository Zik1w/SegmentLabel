# -*- Mode:python; c-file-style:"gnu"; indent-tabs-mode:nil -*- */

import sys
import time
import argparse
import traceback
import pyndn

from pyndn import Interest
from pyndn import Name
from pyndn import Face



class Consumer(object):

    def __init__(self, prefix):
        self.prefix = Name(prefix)
        self.outstanding = dict()
        self.isDone = False
        self.face = Face()


    #event loop, running forever in this application
    def run(self):
        try:
            self._sendNextInterest(self.prefix.append(pyndn.Name.Component.fromSequenceNumber(1)))
            # self._sendNextInterest(self.prefix)


            while not self.isDone:
                self.face.processEvents()
                time.sleep(0.01)

        except RuntimeError as e:
            print("ERROR: %s" % e)

    def _sendNextInterest(self, name):
        interest = Interest(name)
        uri = name.toUri()

        interest.setInterestLifetimeMilliseconds(4000*100)
        interest.setMustBeFresh(False)

        if uri not in self.outstanding:
            self.outstanding[uri] = 1

        self.face.expressInterest(interest, self._onData, self._onTimeout)
        print("Sent Interest for %s" % uri)

    def _onData(self, interest, data):
        payload = data.getContent()
        name = data.getName()

        print("Received data: ", payload.toRawStr())
        del self.outstanding[name.toUri()]

        self.isDone = True

    def _onTimeout(self, interest):
        name = interest.getName()
        uri = name.toUri()

        print("TIMEOUT #%d: %s" % (self.outstanding[uri], uri))
        self.outstanding[uri] += 1

        if self.outstanding[uri] <= 3:
            self._sendNextInterest(name)
        else:
            self.isDone = True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse command line args for ndn consumer')
    parser.add_argument("-u", "--uri", required=True, help='ndn name to retrieve')

    args = parser.parse_args()

    try:
        uri = args.uri
        Consumer(uri).run()

    except:
        traceback.print_exc(file=sys.stdout)
        print("Error parsing command line arguments")
        sys.exit(1)