#!/usr/bin/env python

# mikrotik_control.py

"""A subclass of HostControl for sending commands to a Mikrotik router.

Written by jwiggins@inveneo.org 2011-2012
"""

from __future__ import with_statement
import os
import sys
import socket
import ipaddr
import crawler_conf
import crawler_util
from host_control import HostControl, HostControlError
from mikrotik_api_client import ApiRos

API_PORT = 8728 

class MikrotikRouter(HostControl):
    """Controls a Mikrotik router"""

    def __init__(self, hostname, ipaddress, pwd,
                       max_uptime=crawler_util.SEVEN_DAYS):
        HostControl.__init__(self, hostname, ipaddress,
                               crawler_conf.USERNAME_MIKROTIK, pwd, max_uptime)
        self.host_make  = crawler_util.HOST_MAKE_MIKROTIK
        self.version  = None
        self.hardware = None

    def get_version(self):
        if self.version == None:
            result = self.ssh_command('system resource print; quit')
            line = result[1]
            self.version = line.split(':')[1].strip().strip('"')
        return self.version

    def get_hardware(self):
        if self.hardware == None:
            result = self.ssh_command('system resource print; quit')
            if len(result) > 14:
                line = result[14]
                self.hardware = line.split(':')[1].strip().strip('"')
            else:
                raise HostControl.HostControlError((
                        'Error parsing system resource printout'))
        return self.hardware

    def get_uptime(self):
        """This thing is a bear to parse"""
        result = self.ssh_command('system resource print; quit')
        line = result[0]
        str = line.split(':')[1].strip()
        parts = {'w':0, 'd':0, 'h':0, 'm':0, 's':0}
        sum = 0
        for i in range(len(str)):
            c = str[i]
            if c.isdigit():
                sum = sum * 10 + int(c)
            elif c in parts.keys():
                parts[c] = sum
                sum = 0
            else:
                raise HostControl.HostControlError((
                        'Error parsing uptime string %s' % str))
        weeks = parts['w']
        days  = parts['d'] + weeks * 7
        hours = parts['h'] + days * 24
        mins  = parts['m'] + hours * 60
        return parts['s'] + mins * 60

    def get_adjacency(self):
        """Return OSPF neighbor adjacency time"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((str(self.ipaddress), API_PORT))
        apiros = ApiRos(s)
        apiros.login(self.user, self.pwd)
        apiros.writeSentence('/routing/ospf/neighbor/print')
        return 1

    def _backup_file_stem(self):
        return '%s_%s_%s' % (self.hostname,
                             self.get_hardware(),
                             self.get_version())

    def _backup_binary(self, dst_dir):
        dst_file = '%s.backup' % self._backup_file_stem()
        src_dir = None
        src_file = 'crawler.backup'
        self.ssh_command('system backup save name=crawler; quit')
        self._safe_sftp(src_dir, src_file, dst_dir, dst_file)
        return src_file

    def _backup_config(self, dst_dir):
        dst_file = '%s.config' % self._backup_file_stem()
        config = self.ssh_command('export; quit')
        with open(os.path.join(dst_dir, dst_file), 'w') as outfile:
            for line in config:
                clean = line.rstrip()
                if clean != 'interrupted':
                    outfile.write(clean)
                    outfile.write('\n')
        return 'export'

    def backup(self, backup_root):
        dst_dir = HostControl.backup(self, backup_root)
        fileb = self._backup_binary(dst_dir)
        filec = self._backup_config(dst_dir)
        return '%s+%s' % (fileb, filec)

    def reboot(self, tick):
        return HostControl.reboot(self, 'system reboot ; beep', 10, tick)

if __name__ == '__main__':

    if len(sys.argv) < 3:
        sys.exit('usage: %s ipaddress password [reboot]' % sys.argv[0])
    ip  = ipaddr.IPv4Address(sys.argv[1])
    pwd = sys.argv[2]
    reboot = (len(sys.argv) > 3 and sys.argv[3] == 'reboot')

    router = MikrotikRouter('MyRouter', ip, pwd)
    if not router.is_pingable():
        sys.exit('CANNOT PING')

    print 'Version =', router.get_version()
    print 'Hardware =', router.get_hardware()
    print 'Uptime about', crawler_util.rough_timespan(router.get_uptime())
    print 'Adjacency:'
    print router.get_adjacency()
    if reboot:
        print router.backup('.')
        print router.reboot(True)
