#!/usr/bin/env python

# h3c_control.py

"""A subclass of HostControl for sending commands to an H3C switch.

Written by jwiggins@inveneo.org 2011-2012
"""

import os
import re
import sys
import ipaddr
import pexpect
import crawler_conf
import inveneo_const
import inveneo_utils
from host_control import HostControl, HostControlError

class H3CSwitch(HostControl):
    """Controls an H3C switch"""

    def __init__(self, hostname, ipaddress, pwd,
                       max_uptime=inveneo_const.SEVEN_DAYS):
        HostControl.__init__(self, hostname, ipaddress,
                                   crawler_conf.USERNAME_H3C, pwd, max_uptime)
        self.host_make = inveneo_const.HOST_MAKE_H3C
        self.version = None
        self.hardware = None

    def _sanitize(self, raw_output):
        '''sanitize ugly H3C output'''
        lines = raw_output.split('\n')
        output = []
        for line in lines:
            s = line.strip()
            if s: output.append(s)
        return output

    def versionCB(self, child):
        """command line interaction to pull version lines"""

        PROMPT = '<[\w-]+>'
        child.expect(PROMPT)

        child.sendline('display version')
        child.expect(PROMPT)
        versions = []
        for line in self._sanitize(child.before):
            if line.find('Version') >= 0:
                versions.append(line)

        child.sendline('quit')
        child.expect([pexpect.EOF])
        return versions

    def get_version(self):
        if self.version == None:
            versions = self.ssh_command(None, self.versionCB)
            pattern = '^Comware Software, Version (\S+), Release (\S+)$'
            for line in versions:
                match = re.search(pattern, line)
                if match:
                    self.version = match.group(1)
                    break
        return self.version

    def get_hardware(self):
        if self.hardware == None:
            self.hardware = 'UNDEFINED'
        return self.hardware

    def _computeUptime(self, line):
        uptime = 0
        number = 0
        for part in line.split():
            if part.isdigit():
                number = int(part)
            elif part.startswith('week'):
                uptime += number * 60 * 60 * 24 * 7
            elif part.startswith('day'):
                uptime += number * 60 * 60 * 24
            elif part.startswith('hour'):
                uptime += number * 60 * 60
            elif part.startswith('minute'):
                uptime += number * 60
        return uptime

    def uptimeCB(self, child):
        """command line interaction to pull the uptime"""

        # wait for the prompt
        PROMPT = '<[\w-]+>'
        child.expect(PROMPT)

        child.sendline('display version')
        child.expect(PROMPT)
        uptime = 0
        pattern = '^H3C (\S+) uptime is '
        for line in self._sanitize(child.before):
            if re.search(pattern, line):
                uptime = self._computeUptime(line)
                break

        child.sendline('quit')
        child.expect([pexpect.EOF])
        return uptime

    def get_uptime(self):
        return self.ssh_command(None, self.uptimeCB)

    def configFilenameCB(self, child):
        """command line interaction to pull the config filename"""

        # wait for the prompt
        PROMPT = '<[\w-]+>'
        try:
            reply = child.expect([pexpect.TIMEOUT, PROMPT])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        child.sendline('display startup')
        try:
            reply = child.expect([pexpect.TIMEOUT, PROMPT])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        filename = ''
        for line in self._sanitize(child.before):
            if line.startswith('Next main startup saved-configuration file:'):
                parts = line.split()
                filename = parts[-1].split('/')[-1]
                break

        child.sendline('quit')
        child.expect([pexpect.EOF])
        return filename

    def get_config_filename(self):
        return self.ssh_command(None, self.configFilenameCB)

    def _start_sftp_server_CB(self, child):
        child.expect('<[\w-]+>')
        child.sendline('system-view')
        child.expect('\[[\w-]+\]')
        child.sendline('sftp server enable')
        child.expect('\[[\w-]+\]')
        child.sendline('quit')
        child.expect('<[\w-]+>')
        child.sendline('quit')
        child.expect([pexpect.EOF])

    def _start_sftp_server(self):
        return self.ssh_command(None, self._start_sftp_server_CB)

    def backup(self, backup_root):
        dst_dir = HostControl.backup(self, backup_root)
        dst_file = '%s.cfg' % self.hostname
        src_dir = None
        src_file = self.get_config_filename()
        self._start_sftp_server()
        self._safe_sftp(src_dir, src_file, dst_dir, dst_file)
        return src_file

    def rebootCB(self, child):
        """command line interaction to reboot the device"""

        # wait for the prompt
        PROMPT = '<[\w-]+>'
        try:
            reply = child.expect([pexpect.TIMEOUT, PROMPT])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        # send command to save running configuration
        child.sendline('save safely main')
        try:
            reply = child.expect([pexpect.TIMEOUT, 'Are you sure\?\[Y/N\]'])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        child.sendline('Y')
        try:
            reply = child.expect([pexpect.TIMEOUT, 'press the enter key\):'])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        child.sendline('')
        try:
            reply = child.expect([pexpect.TIMEOUT, PROMPT])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        # send command to reboot
        child.sendline('reboot')
        try:
            reply = child.expect([pexpect.TIMEOUT, 'Continue\? \[Y/N\]'])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        child.sendline('Y')
        try:
            reply = child.expect([pexpect.TIMEOUT,
                                  'Continue\? \[Y/N\]',
                                  'Reboot device by command.'])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)
        elif reply == 1: # Asking again
            child.sendline('Y')
            try:
                reply = child.expect([pexpect.TIMEOUT,
                                      'Reboot device by command.'])
            except pexpect.ExceptionPexpect, err:
                raise HostControlError(HostControlError.SSH,
                                       self.decode_err(err))
            if reply == 0: # Timeout
                raise HostControlError(HostControlError.TIMEOUT)

        child.close()
        return ''

    def reboot(self, tick):
        """login and then transfer control to callback"""
        return HostControl.reboot(self, None, 10, tick, self.rebootCB)

    def commandCB(self, child, command):
        """arbitrary single command line interaction"""

        # wait for the prompt
        PROMPT = '<[\w-]+>'
        child.expect(PROMPT)

        child.sendline(command)
        child.expect(PROMPT)
        result = child.before

        child.sendline('quit')
        child.expect([pexpect.EOF])
        return result

    def command(self, command):
        """login and then transfer to lambda, which passes extra parameter"""
        return self.ssh_command(None,
                                lambda child: self.commandCB(child, command))

if __name__ == '__main__':

    if len(sys.argv) < 3:
        sys.exit('usage: %s ipaddress password [reboot]' % sys.argv[0])
    ip  = ipaddr.IPv4Address(sys.argv[1])
    pwd = sys.argv[2]
    reboot = (len(sys.argv) > 3 and sys.argv[3] == 'reboot')

    switch = H3CSwitch('MySwitch', ip, pwd)
    if not switch.is_pingable():
        sys.exit('CANNOT PING')

    print 'Version =', switch.get_version()
    print 'Hardware =', switch.get_hardware()
    print 'Uptime about', inveneo_utils.rough_timespan(switch.get_uptime())
    print 'Device:', switch.command('display device')
    if reboot:
        print 'Backup config =', switch.backup('.')
        sys.stdout.write('Reboot: ')
        switch.reboot(True)
