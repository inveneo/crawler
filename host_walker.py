#!/usr/bin/env python

# host_walker.py

"""A generator that walks hosts in a network in depth-first fashion.

By "depth-first" we mean "furthest downstream first".

Right now it's pretty brain-dead, not doing depth-first, but instead going in
order of sorted IP address.

Written by jwiggins@inveneo.org 2011-2012
"""

import sys
import ipaddr
import crawler_conf
import inveneo_const
from xml.etree import ElementTree

# for parsing OpenNMS XML
NAMESPACE = '{http://xmlns.opennms.org/xsd/config/model-import}'
NODE      = NAMESPACE + 'node'
INTERFACE = NAMESPACE + 'interface'

class HostNode(object):
    """Represents one OpenNMS node"""

    def __init__(self, xml_node, host_make):
        self.host_make  = host_make
        self.hostname   = xml_node.attrib['node-label']
        interface       = xml_node.find(INTERFACE)
        self.ip_addr    = ipaddr.IPv4Address(interface.attrib['ip-addr'])
        self.password   = crawler_conf.NODE_PASSWORD
        self.max_uptime = crawler_conf.MAX_UPTIME

    def __str__(self):
        return '%s %s %s' % (self.host_make, self.hostname, self.ip_addr)

class OpenNMSFile(object):
    """Represents the contents of one OpenNMS XML provisioning file"""

    def __init__(self, xml_file):
        self.xmlFile = xml_file
        self.host_nodes = []
        et = ElementTree.parse(xml_file)
        root = et.getroot()
        foreign_source = root.attrib['foreign-source']
        if foreign_source in crawler_conf.FOREIGN_SOURCES_UBIQUITI:
            self.host_make = inveneo_const.HOST_MAKE_UBIQUITI
        elif foreign_source in crawler_conf.FOREIGN_SOURCES_H3C:
            self.host_make = inveneo_const.HOST_MAKE_H3C
        elif foreign_source in crawler_conf.FOREIGN_SOURCES_MIKROTIK:
            self.host_make = inveneo_const.HOST_MAKE_MIKROTIK
        else:
            self.host_make = inveneo_const.HOST_MAKE_UNKNOWN

        for xml_node in et.findall(NODE):
            host_node = HostNode(xml_node, self.host_make)
            self.host_nodes.append(host_node)

    def __iter__(self):
        for host_node in self.host_nodes:
            yield host_node

class HostWalker(object):
    """Compiles a list of all hosts, organizes them, and allows iteration"""

    def __init__(self, opennms_files, start_after_ip=None):
        '''reads XML files to populate dictionary of unique and dup hosts'''
        self.start_after_ip = start_after_ip
        self.unique_hosts = {}
        self.duplicates = {}
        for opennms_file in opennms_files:
            host_list = OpenNMSFile(opennms_file)
            for host in host_list:
                key = host.ip_addr
                if self.unique_hosts.has_key(key):
                    if not self.duplicates.has_key(key):
                        self.duplicates[key] = [host]
                    else:
                        self.duplicates[key].append(host)
                else:
                    self.unique_hosts[key] = host

    def __iter__(self):
        '''iterates through unique hosts'''
        sorted_keys = sorted(self.unique_hosts.keys())

        # find where we left off and split the list
        start = 0
        if self.start_after_ip:
            try:
                index = sorted_keys.index(self.start_after_ip)
                start = (index + 1) % len(sorted_keys)
            except:
                start = 0
        tail = sorted_keys[:start]
        head = sorted_keys[start:]

        for key in head + tail:
            yield self.unique_hosts[key]

    def host_count(self):
        '''accessor so folks don't have to mess with self data'''
        return len(self.unique_hosts)

if __name__ == '__main__':

    if len(sys.argv) < 2:
        sys.exit('usage: %s opennms_file ...' % sys.argv[0])

    private_list = []
    host_walker = HostWalker(sys.argv[1:])
    for host in host_walker:
        print host
        private_list.append(host)
    if host_walker.duplicates:
        print '=== DUPLICATES ==='
        for key in host_walker.duplicates:
            for host in host_walker.duplicates[key]:
                print host

    # here we test the "start_after_ip" feature
    index = len(private_list) / 2
    median_host = private_list[index]
    print
    print 'Median host is:', median_host
    print

    host_walker = HostWalker(sys.argv[1:], median_host.ip_addr)
    for host in host_walker:
        print host
