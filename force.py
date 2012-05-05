#
#  force : openflow application
#

from nox.lib.core import *
from nox.lib.packet.ethernet     import ethernet
from nox.lib.packet.packet_utils import mac_to_str, mac_to_int

from twisted.python import log
from time import time
from socket import ntohl
from struct import unpack

import logging

FDB_LIFETIME  = 5
FLOW_LIFETIME = 5

LOG_FILENAME  = '/var/log/nox/force.log'


# self.fdb is Forwarding Information Base
# fdb -> DPID -> MAC = Port


class force (Component):

    def __init__ (self, context) :




        self.log = logging.getLogger ('nox.coreapps.mods.force')
        self.fdb = {}
        Component.__init__ (self, context)


    def install (self) :

        self.register_for_datapath_join (self.process_datapath_join)
        self.register_for_datapath_leave (self.process_datapath_leave)
        self.register_for_packet_in (self.process_packet_in)
        self.post_callback (1, self.process_timer_call_back)


    def process_packet_in (self, dpid, inport, reason, length, bufid, packet) :
        
        # Create New Fdb for switch if it is not created
        if not self.fdb.has_key (dpid) :
            self.fdb[dpid] = {}
            
        if packet.type == ethernet.LLDP_TYPE :
            return CONTINUE

        self.l2_learning (dpid, inport, packet)
        self.l2_forwarding (dpid, inport, packet, bufid)


    def l2_learning (self, dpid, inport, packet) :
        
        srcmac = packet.src.tostring ()
        
        if self.fdb.has_key (dpid) :
            self.fdb[dpid][srcmac] = [inport, FDB_LIFETIME]
        return


    def l2_forwarding (self, dpid, inport, packet, bufid) :
        
        dstmac = packet.dst.tostring ()
        
        if not self.fdb.has_key (dpid) :
            self.log.info ('packet from invalid DPID %s' % (dpid))
            return
        
        if self.fdb[dpid].has_key (dstmac) :
            (outport, lifetime) = self.fdb[dpid][dstmac]
            flow = extract_flow (packet)
            flow[core.IN_PORT] = inport

            actions = [[openflow.OFPAT_OUTPUT, [0, outport]]]
            self.install_datapath_flow (dpid, flow, FLOW_LIFETIME,
                                        openflow.OFP_FLOW_PERMANENT, actions,
                                        bufid, openflow.OFP_DEFAULT_PRIORITY,
                                        inport, packet.arr)
        else :
            self.send_openflow (dpid, bufid, packet.arr, openflow.OFPP_FLOOD, inport)

        return

    
    def process_timer_call_back (self) :
        
        for dpid in self.fdb.keys () :
            for mac in self.fdb[dpid].keys () :

                self.fdb[dpid][mac][1] -= 1

                if self.fdb[dpid][mac][1] < 0 :
                    del self.fdb[dpid][mac]
                    
        return


    def process_datapath_join (self, dpid, status) :

        self.log.info ('new Openflow Switch %s has Joined' % (dpid))
        self.fdb[dpid] = {}
        return

    
    def process_datapath_leave (self, dpid) :

        self.log.info ('Openflow Switch %s has Leaved' % (dpid))
        if self.fdb.has_key (dpid) :
            del self.fdb[dpid]

        return


    def getInterface (self) :
        return str (force)


    
def getFactory () :
    class Factory :
        def instance (self, context) :
            return force (context)

    return Factory ()
