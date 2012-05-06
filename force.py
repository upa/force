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


from nox.coreapps.force.fdb import fdb

LOG_FILENAME  = '/var/log/nox/force.log'
FLOW_LIFETIME = 10


class force (Component):

    def __init__ (self, context) :

        self.log = logging.getLogger ('nox.coreapps.mods.force')
        self.fdb = fdb ()

        self.fdb.install_mac_nwname_binding ('00:11:25:87:f6:e9', 'target1')
        self.fdb.install_mac_nwname_binding ('00:11:25:87:f6:f0', 'target2')
        self.fdb.install_mac_nwname_binding ('00:11:25:87:f6:f1', 'target3')

        self.fdb.install_mac_nwname_binding ('a4:ba:db:19:e1:78', 'target1')
        self.fdb.install_mac_nwname_binding ('a4:ba:db:19:e1:79', 'target2')
        self.fdb.install_mac_nwname_binding ('a4:ba:db:19:e1:80', 'target3')

        Component.__init__ (self, context)


    def install (self) :

        self.register_for_datapath_join (self.process_datapath_join)
        self.register_for_datapath_leave (self.process_datapath_leave)
        self.register_for_packet_in (self.process_packet_in)
        self.post_callback (1, self.process_timer_call_back)


    def process_packet_in (self, dpid, inport, reason, length, bufid, packet) :
        
        # Create New Fdb for switch if it is not created
        if packet.type == ethernet.LLDP_TYPE :
            return CONTINUE

        if packet.type == ethernet.ARP_TYPE :
            print "ARP PACKET"
            
        self.l2_learning (dpid, inport, packet)
        self.l2_forwarding (dpid, inport, packet, bufid)

        return CONTINUE


    def l2_learning (self, dpid, inport, packet) :
        self.fdb.update (dpid, mac_to_str (packet.src), inport)
        return

    def l2_forwarding (self, dpid, inport, packet, bufid) :
        
        [forward_type, outports] = self.fdb.search (dpid, 
                                                    mac_to_str (packet.src), 
                                                    mac_to_str (packet.dst), 
                                                    inport)
        
        if forward_type == 'FLOOD' :
            actions = []
            for port in outports :
                actions.append ([openflow.OFPAT_OUTPUT, [0, port]])

            print 'flooding dipd=%x dstmac=%s' % (dpid, mac_to_str (packet.dst))
            print outports
            self.send_openflow (dpid, bufid, packet.arr, actions, inport)

        elif forward_type == 'UNICAST' :
            flow = extract_flow (packet)
            flow[core.IN_PORT] = inport
        
            actions = [[openflow.OFPAT_OUTPUT, [0, outports.pop ()]]]
            self.install_datapath_flow (dpid, flow, FLOW_LIFETIME,
                                        openflow.OFP_FLOW_PERMANENT, actions,
                                        bufid, openflow.OFP_DEFAULT_PRIORITY,
                                        inport, packet.arr)

        return

    
    def process_timer_call_back (self) :
        self.fdb.decrement_entry_lifetime ()


    def process_datapath_join (self, dpid, status) :
        self.log.info ('new Openflow Switch %s has Joined' % (dpid))
        self.fdb.install_dpid (dpid)
        self.fdb.install_aggregate_port (dpid, 1)
        return

    
    def process_datapath_leave (self, dpid) :
        self.log.info ('Openflow Switch %s has Leaved' % (dpid))
        self.fdb.uninstall_dpid (dpid)
        self.fdb.uninstall_aggregate_port (dpid, 1)

        return

    def getInterface (self) :
        return str (force)


    
def getFactory () :
    class Factory :
        def instance (self, context) :
            return force (context)

    return Factory ()
