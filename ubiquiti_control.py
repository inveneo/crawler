#!/usr/bin/env python

# ubiquiti_control.py

"""A subclass of HostControl for sending commands to a Ubiquiti radio.

Written by jwiggins@inveneo.org 2011-2012
"""

import sys
import ipaddr
import crawler_conf
import crawler_util
from host_control import HostControl, HostControlError

class UbiquitiRadio(HostControl):
    """Controls a Ubiquiti radio"""

    def __init__(self, hostname, ipaddress, pwd,
                       max_uptime=crawler_util.SEVEN_DAYS):
        HostControl.__init__(self, hostname, ipaddress,
                               crawler_conf.USERNAME_UBIQUITI, pwd, max_uptime)
        self.host_make  = crawler_util.HOST_MAKE_UBIQUITI
        self.version = None
        self.hardware = None

    def get_version(self):
        if self.version == None:
            result = self.ssh_command('cat /etc/version')
            line = result[0].strip()
            self.version = line.split('v')[1]
        return self.version

    def get_hardware(self):
        if self.hardware == None:
            result = self.ssh_command('cat /etc/board.inc')
            line = result[2].strip()
            (key, val) = line.split('=')
            self.hardware = val.strip(';').strip('"')
        return self.hardware

    def get_uptime(self):
        result = self.ssh_command('cat /proc/uptime')
        seconds, idle = result[0].split()
        return int(float(seconds))

    def backup(self, backup_root):
        src_dir = '/tmp'
        src_file = 'system.cfg'
        dst_dir = HostControl.backup(self, backup_root)
        dst_file = '%s_%s.cfg' % (self.hostname, self.get_version())
        self._safe_scp(src_dir, src_file, dst_dir, dst_file)
        return src_file

    def reboot(self, tick):
        return HostControl.reboot(self, 'reboot', 10, tick)

if __name__ == '__main__':

    if len(sys.argv) < 3:
        sys.exit('usage: %s ipaddress password [reboot]' % sys.argv[0])
    ip  = ipaddr.IPv4Address(sys.argv[1])
    pwd = sys.argv[2]
    reboot = (len(sys.argv) > 3 and sys.argv[3] == 'reboot')

    radio = UbiquitiRadio('MyRadio', ip, pwd)
    if not radio.is_pingable():
        sys.exit('CANNOT PING')

    print 'Version =', radio.get_version()
    print 'Hardware =', radio.get_hardware()
    print 'Uptime about', crawler_util.rough_timespan(radio.get_uptime())
    if reboot:
        print radio.backup('.')
        print radio.reboot(True)
