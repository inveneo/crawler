#!/usr/bin/env python
 
# host_control.py

"""Base classes for controlling various hardware units.
This is very generic, and gets subclassed.

Written by jwiggins@inveneo.org 2011-2012
"""

import os
import sys
import time
import pexpect
import tempfile
import subprocess
import crawler_util

SSH_NEWKEY      = '(?i)are you sure you want to continue connecting'
PASSWORD_PROMPT = '(?i)password'
TEMPFILE        = '/tmp/host_control.tmp'

class HostControlError(BaseException):
    """The exception type for this module"""
    NOT_IMPL = 'Not Implemented'
    SSH      = 'SSH Error'
    TIMEOUT  = 'Timeout'
    HSHAKE   = 'Handshake Error'
    PASSWD   = 'Password Error'
    NOPING   = 'Cannot Ping'

    def __init__(self, code, tail=None):
        self.code = code
        self.tail = tail

    def __str__(self):
        if self.tail is None:
            return self.code
        else:
            return '%s: %s' % (self.code, self.tail)

class HostControl(object):
    """Controls a remote host"""

    MAX_REBOOT_WAIT_SEC = 60 * 20 # 20 min wait for reboot (seconds)
    FULL_BOOT_WAIT      = 60      # extra wait from pingable to fully booted

    def __init__(self, hostname, ipaddress, user, pwd,
                       max_uptime=crawler_util.SEVEN_DAYS):
        self.hostname   = hostname
        self.ipaddress  = ipaddress
        self.user       = user
        self.pwd        = pwd
        self.max_uptime = max_uptime
        self.host_make  = crawler_util.HOST_MAKE_UNKNOWN # set in subclass

    ##### ABSTRACT METHODS: Override these in your subclass #####

    def get_version(self):
        """Get the OS or firmware version from the host"""
        raise HostControlError(HostControlError.NOT_IMPL)

    def get_hardware(self):
        """Get the hardware version from the host"""
        raise HostControlError(HostControlError.NOT_IMPL)

    def get_uptime(self):
        """Get the uptime of the host"""
        raise HostControlError(HostControlError.NOT_IMPL)

    ##### PRIVATE METHODS #####

    def is_pingable(self):
        ret = subprocess.call("ping -n -c 1 %s" % self.ipaddress,
                              shell=True,
                              stdout=open('/dev/null', 'w'),
                              stderr=subprocess.STDOUT)
        return (ret == 0)

    def decode_err(self, err):
        """Parse the ugly pexpect exception"""
        message = []
        lines = err.__dict__['value']
        for line in lines.split('\n'):
            parts = line.split(':')
            if parts[0] == 'before (last 100 chars)':
                message = [':'.join(parts[1:])]
            elif parts[0] == 'after':
                break
            elif len(message) > 0:
                message.append(line)
        return ''.join(message)

    def ssh_command(self, command, callback=None):
        """Use pexpect to interact with remote SSH server"""

        if command:
            child = pexpect.spawn('ssh %s@%s %s' %
                                        (self.user, self.ipaddress, command))
        else:
            child = pexpect.spawn('ssh %s@%s' % (self.user, self.ipaddress))
        # uncomment this to see more verbosity
        #child.logfile = sys.stdout

        # start the connection; expect password prompt
        try:
            reply = child.expect([pexpect.TIMEOUT, SSH_NEWKEY, PASSWORD_PROMPT])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))

        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        elif reply == 1: # SSH does not have the public key cached
            try:
                child.sendline('yes')
                child.expect(PASSWORD_PROMPT)
            except pexpect.ExceptionPexpect:
                raise HostControlError(HostControlError.HSHAKE)

        # send password; either get command output or pass child to callback
        child.sendline(self.pwd)
        lines = []
        if command:
            try:
                reply = child.expect([pexpect.EOF,
                                     '(?i)Permission denied, please try again'])
            except pexpect.ExceptionPexpect, err:
                raise HostControlError(HostControlError.PASSWD,
                                       self.decode_err(err))
            if reply == 0: # command finished
                before = child.before.split('\n')
                lines = before[1:-1] # tear off garbage at beginning and end
            elif reply == 1: # bad password
                raise HostControlError(HostControlError.PASSWD)
        else:
            lines = callback(child)
        child.close(force=True)
        return lines

    def _scp(self, src_dir, src_file, dst_dir, dst_file):
        """A little SCP utility that uses pexpect to pull one file"""
        child = pexpect.spawn('scp %s@%s:%s %s' % \
                                  (self.user,
                                   self.ipaddress,
                                   os.path.join(src_dir, src_file),
                                   os.path.join(dst_dir, dst_file)))
        # uncomment this to see more verbosity
        #child.logfile = sys.stdout

        # start the connection; expect password prompt
        try:
            reply = child.expect([pexpect.TIMEOUT, SSH_NEWKEY, PASSWORD_PROMPT])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))

        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)

        elif reply == 1: # SSH does not have the public key cached
            try:
                child.sendline('yes')
                child.expect(PASSWORD_PROMPT)
            except pexpect.ExceptionPexpect:
                raise HostControlError(HostControlError.HSHAKE)

        # send password and wait for command to exit
        child.sendline(self.pwd)
        child.expect([pexpect.EOF])

    def _safe_scp(self, src_dir, src_file, dst_dir, dst_file):
        """Uses SCP to a temp file and then moves the temp file if OK"""
        (tmp_dir, tmp_file) = os.path.split(TEMPFILE)
        try:
            self._scp(src_dir, src_file, tmp_dir, tmp_file)
            os.rename(TEMPFILE, os.path.join(dst_dir, dst_file))
        except:
            # file transfer failed: remove temp file
            if os.path.exists(TEMPFILE):
                os.unlink(TEMPFILE)
            raise

    def _sftp(self, src_dir, src_file, dst_dir, dst_file):
        """A little SFTP utility that uses pexpect to pull one file"""
        child = pexpect.spawn('sftp %s@%s' % (self.user, self.ipaddress))
        try:
            reply = child.expect([pexpect.TIMEOUT, PASSWORD_PROMPT])
        except pexpect.ExceptionPexpect, err:
            raise HostControlError(HostControlError.SSH, self.decode_err(err))
        if reply == 0: # Timeout
            raise HostControlError(HostControlError.TIMEOUT)
        child.sendline(self.pwd)
        child.expect('sftp>')
        if src_dir:
            child.sendline('cd %s' % src_dir)
            child.expect('sftp>')
        if dst_dir:
            child.sendline('lcd %s' % dst_dir)
            child.expect('sftp>')
        child.sendline('get %s %s' % (src_file, dst_file))
        child.expect('sftp>')
        child.sendline('quit')
        child.expect([pexpect.EOF])
        child.close()

    def _safe_sftp(self, src_dir, src_file, dst_dir, dst_file):
        """Uses SFTP to a temp file and then moves the temp file if OK"""
        (tmp_dir, tmp_file) = os.path.split(TEMPFILE)
        try:
            self._sftp(src_dir, src_file, tmp_dir, tmp_file)
            os.rename(TEMPFILE, os.path.join(dst_dir, dst_file))
        except:
            # file transfer failed: remove temp file
            if os.path.exists(TEMPFILE):
                os.unlink(TEMPFILE)
            raise

    def backup(self, backup_root):
        """Subclasses should call this first, to create place for backup"""
        backup_root = os.path.abspath(backup_root)
        backup_path = os.path.join(backup_root, self.host_make)
        if not os.path.isdir(backup_path):
            os.mkdir(backup_path)
        return backup_path

    def reboot(self, rebootStr, rebootWait, tick, rebootCB=None):
        """Reboot the host"""
        if not self.is_pingable():
            raise HostControlError(HostControlError.NOPING)

        # issue the reboot command (may raise exception)
        if rebootStr:
            self.ssh_command(rebootStr)
        else:
            self.ssh_command(None, rebootCB)

        # wait for reboot command to take the machine down
        time.sleep(rebootWait)

        # wait for the Second Coming
        start_wait = time.time()
        resurrected = False
        while not resurrected:

            # do not wait forever for the machine to come back
            if time.time() - start_wait > self.MAX_REBOOT_WAIT_SEC:
                return False

            # show waiting progress
            if tick:
                sys.stdout.write('*')
                sys.stdout.flush()

            # ping the machine
            resurrected = self.is_pingable()

        time.sleep(self.FULL_BOOT_WAIT)
        return True

if __name__ == '__main__':

    if len(sys.argv) < 5:
        sys.exit('usage: %s HOST_IP USER PWD COMMAND...' % sys.argv[0])

    ipaddr  = sys.argv[1]
    user    = sys.argv[2]
    pwd     = sys.argv[3]
    command = ' '.join(sys.argv[4:])

    control = HostControl('unknown', ipaddr, user, pwd)

    if not control.is_pingable():
        sys.exit('Cannot ping %s' % ipaddr)

    lines = control.ssh_command(command)
    if lines:
        for line in lines:
            print line
