# crawler_conf.py -- configuration for network host crawler

# passwords
NODE_PASSWORD = 'all-node-password'

# usernames
USERNAME_H3C      = 'admin'
USERNAME_MIKROTIK = 'admin'
USERNAME_UBIQUITI = 'ubnt'

# maximum uptime (seconds)
MAX_UPTIME = 7 * 24 * 60 * 60

# OpenNMS foreign-source values
FOREIGN_SOURCES_H3C      = ['h3c']
FOREIGN_SOURCES_MIKROTIK = ['mikrotik']
FOREIGN_SOURCES_UBIQUITI = ['cpes', 'ubiquiti']

# paths on this server
PATH_SSH_KEYGEN = '/usr/bin/ssh-keygen'
