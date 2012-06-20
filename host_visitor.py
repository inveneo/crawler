#!/usr/bin/env python

# host_visitor.py

"""Visits hosts in a network, in round-robin fashion, doing housekeeping.

By "round-robin" we mean it saves where it left off so that it can resume there
on its next run. This is done to avoid starvation.

The housekeeping it does at each host is done in the "visitation" function.

Written by jwiggins@inveneo.org 2011-2012
"""

from __future__ import with_statement
import os
import sys
import string
import random
import traceback
import host_walker
import crawler_conf
import crawler_util
from ipaddr import IPv4Address
from subprocess import Popen, PIPE
from h3c_control import H3CSwitch
from host_control import HostControlError
from mikrotik_control import MikrotikRouter
from ubiquiti_control import UbiquitiRadio

PRINTWORTHY_CHARS = string.digits + string.letters + string.punctuation

def get_last_visited(state_file):
    """Pull IP address of last visited host from given file"""
    if not os.path.exists(state_file): return None
    try:
        with open(state_file, 'r') as infile:
            line = infile.readline().strip()
    except:
        return None
    if not line: return None
    return IPv4Address(line)

def set_last_visited(state_file, last_visited_ip):
    """Stash IP address of last visited host into given file"""
    with open(state_file, 'w') as outfile:
        outfile.write('%s\n' % IPv4Address(last_visited_ip))

def emit(obj):
    """For unbuffered writing to stdout"""
    sys.stdout.write(str(obj))
    sys.stdout.flush()

def emit_tab(obj):
    """For tab-separated values"""
    emit(obj)
    emit('\t')

def emit_fail(obj):
    """Standard error format, for easy search"""
    emit('FAIL:')
    emit_tab(obj)

def ask_exception():
    """Create succinct exception tuple"""
    exctype, value = sys.exc_info()[:2]
    first_line = str(value).split('\n')[0]
    chars = []
    for i in range(len(first_line)):
        if first_line[i] in PRINTWORTHY_CHARS:
            chars.append(first_line[i])
        else:
            chars.append(' ')
    msg  = ''.join(chars)
    return (exctype.__name__, msg)

def emit_exception(name, msg):
    """Write succinct exception output"""
    emit_fail('%s:%s' % (name, msg))

def query_unit(unit):
    """The unit is online: query it, return uptime"""

    # this first query gets firmware version and also tests the password
    try:
        version = unit.get_version()
    except:
        raise
    emit_tab(version)

    # also query for uptime
    try:
        uptime = unit.get_uptime()
        emit_tab(crawler_util.rough_timespan(uptime))
    except:
        raise
    return uptime

def remove_ssh_key(ip_address):
    """Need to remove stale SSH key for given IP address"""
    sp = Popen([crawler_conf.PATH_SSH_KEYGEN, '-R', str(ip_address)],
               stdout=PIPE, stderr=PIPE)
    return sp.communicate()

def visitation(unit, backup_root, rebootable):
    """Should catch all exceptions and only re-raise Control-C
       Arg: backup_root = where to save backup of config file(s)
       Arg: rebootable = False if reboot should not be attempted
       Return: True if rebooted host, else False"""
    uptime = None

    # ping the unit and query it (which also tests the password)
    try:
        if unit.is_pingable():
            emit_tab('ping')
            uptime = query_unit(unit)
        else:
            emit_fail('no_ping')
            return
    except KeyboardInterrupt:
        # caught control-c; kick it upstairs
        raise KeyboardInterrupt
    except:
        # caught other exception: print it out
        (name, msg) = ask_exception()
        if msg.strip().endswith('Host key verification failed.'):
            (stdout, stderr) = remove_ssh_key(unit.ipaddress)
            msg = msg + stdout + stderr
        emit_exception(name, msg)
        return

    # pull config(s) from unit to keep as backup
    try:
        emit_tab(str(unit.backup(backup_root)))
    except KeyboardInterrupt:
        # caught control-c; kick it upstairs
        raise KeyboardInterrupt
    except:
        # caught other exception: print it out
        (name, msg) = ask_exception()
        emit_exception(name, msg)
        return

    # reboot if past maximum uptime
    if rebootable and uptime and uptime > unit.max_uptime:
        emit_tab('REBOOT')
        try:
            unit.reboot(True)
            return True
        except KeyboardInterrupt:
            # caught control-c; kick it upstairs
            raise KeyboardInterrupt
        except:
            # caught other exception: print it out
            (name, msg) = ask_exception()
            emit_exception(name, msg)
            return False
    return False

if __name__ == '__main__':

    if len(sys.argv) < 3:
        sys.exit('usage: %s state_file backup_root opennms_file ...' % \
                    sys.argv[0])
    state_file  = os.path.abspath(sys.argv[1])
    backup_root = os.path.abspath(sys.argv[2])
    xml_files   = sys.argv[3:]

    try:
        os.makedirs(backup_root)
    except OSError:
        # dir already exists
        if not os.access(backup_root, os.W_OK):
            sys.exit('Cannot write to %s' % backup_root)

    last_visited_ip = get_last_visited(state_file)
    try:
        walker = host_walker.HostWalker(xml_files, last_visited_ip)
        total_units = walker.host_count()
        print 'There are', total_units, 'units to visit'
        reboots = 0
        max_reboots = (total_units / 7) + 1
        print 'Maximum number of reboots is', max_reboots

        # column headings
        emit_tab('Make')
        emit_tab('Host')
        emit_tab('IP')
        emit_tab('Ping')
        emit_tab('Version')
        emit_tab('Uptime')
        emit('Config\n')

        for host in walker:
            if host.host_make == crawler_util.HOST_MAKE_UBIQUITI:
                unit = UbiquitiRadio(host.hostname,
                                     host.ip_addr,
                                     host.password,
                                     host.max_uptime)
            elif host.host_make == crawler_util.HOST_MAKE_H3C:
                unit = H3CSwitch(host.hostname,
                                 host.ip_addr,
                                 host.password,
                                 host.max_uptime)
            elif host.host_make == crawler_util.HOST_MAKE_MIKROTIK:
                unit = MikrotikRouter(host.hostname,
                                      host.ip_addr,
                                      host.password,
                                      host.max_uptime)
            else:
                # unknown make of host: skip it
                continue

            # the first output fields
            emit_tab(host.host_make)
            emit_tab(host.hostname)
            emit_tab(str(host.ip_addr))

            # do the work for this kind of device
            if visitation(unit, backup_root, reboots < max_reboots):
                reboots += 1

            # record having visited this device
            print ''
            last_visited_ip = host.ip_addr

    except KeyboardInterrupt:
        print ''
        pass

    except:
        # eww, some kind of internal error
        print ''
        traceback.print_exc()

    finally:
        if last_visited_ip:
            set_last_visited(state_file, last_visited_ip)
