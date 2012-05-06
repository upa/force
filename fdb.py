
FDB_LIFETIME  = 5

import re

class fdb () :

    def __init__ (self) :
        self.fdb = {}
        self.mdb = {}
        self.ndb = {}
        self.adb = {}

    def install_mac_nwname_binding (self, mac, nwname) :
        self.mdb[mac] = nwname

    def uninstall_mac_nwname_binding (self, mac, nwname) :
        if self.mdb.has_key (mac) :
            del self.mdb[mac]

    def install_dpid (self, dpid) :
        self.ndb[dpid] = {}
        self.fdb[dpid] = {}
        self.adb[dpid] = set ()

    def uninstall_dpid (self, dpid) :
        if self.adb.has_key (dpid) :
            del adb[dpid]

        if self.ndb.has_key (dpid) :
            del ndb[dpid]

        if self.fdb.has_key (dpid) :
            del fdb[dpid]

    def install_aggregate_port (self, dpid, port) :
        self.adb[dpid].add (port)
    
    def uninstall_aggregate_port (self, dpid, port) :
        self.adb[dpid].remove (port)

    def update (self, dpid, srcmacstr, inport) :

        if not self.mdb.has_key (srcmacstr) :
            print "unknown network name mac %s" % (srcmacstr)
            return

        nwname = self.mdb[srcmacstr]

        self.fdb[dpid][srcmacstr] = {
            'PORT' : inport,
            'LIFETIME' : FDB_LIFETIME
            }

        self.ndb[dpid][inport] =  nwname


    def search (self, dpid, srcmacstr, dstmacstr, inport) :

        if not self.mdb.has_key (srcmacstr) :
            print "invalid Src Mac Address %s, NWNAME UNKNOWN" % (srcmacstr)
            return ['INVALID', ([])]

        if not self.mdb.has_key (dstmacstr) :
            print "invalid Dst Mac Address %s, NWNAME UNKNOWN" % (dstmacstr)

        nwname = self.mdb[srcmacstr]

        sendport = set ()
        
        # return value set ([TYPE, ([port1, port2, ...])]) 
        # TYPE is, FLOOD or UNICAST

        if not self.fdb[dpid].has_key (dstmacstr) :
            # this dst mac is not known yet. flooding!
            for port in self.ndb[dpid].keys () :
                if nwname == self.ndb[dpid][port] and port != inport :
                    sendport.add (port)

            sendport.update (self.adb[dpid])

            if inport in sendport :
                sendport.remove (inport)

            return ['FLOOD', sendport]

        else :
            # Unicast !
            sendport.add (self.fdb[dpid][dstmacstr]['PORT'])
            return ['UNICAST', sendport]


    def decrement_entry_lifetime (self) :

        for dpid in self.fdb.keys () :
            for entry in fdb[dpid].keys () :
                fdb[dpid][entry]['LIFETIME'] -= 1
                if fdb[dpid][entry]['LIFETIME'] < 0 :
                    del fdb[dpid][entry]


    def install_mac_nwname_binding_by_configfile (self, configfile) :

        f = open (configfile, 'r')

        for line in f :
            line = line.strip ()
            line = re.sub (r'\t+', ' ', line)
            line = re.sub (r' +', ' ', line)
            
            if re.match (r'^#', line) :
                continue

            sp = line.split (' ')
            if len (sp) < 2 :
                continue
            
            self.install_mac_nwname_binding (sp[0], sp[1])

        f.close ()

