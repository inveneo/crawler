#!/bin/sh

# crawler.sh - Visit network nodes at night: pull configs, reboot long uptime.
#              $1 = Hour to terminate
#              $2 = Minute to terminate
#     Requires the "timeout" command provided by package "timeout"
#     Written by jwiggins 3/14/2012

# paths on this system
BASENAME="/usr/bin/basename"
TIMEOUT="/usr/bin/timeout"

# helper scripts and config files
STATE="/var/inveneo/crawler-last-visited"
BACKUPS="/var/backups/pulled-configs"
VISITOR="/opt/inveneo/crawler/host_visitor.py"

# database of nodes
RADIOS="/etc/opennms/imports/ubiquiti.xml"
ROUTERS="/etc/opennms/imports/mikrotik.xml"
SWITCHES="/etc/opennms/imports/h3c.xml"
XML_FILES="${RADIOS} ${ROUTERS} ${SWITCHES}"

SCRIPT=`${BASENAME} $0`
SIGINT="2"
SIGTERM="15"

# make sure running as root
if [ "$(id -u)" != "0" ] ; then
    echo "${SCRIPT} must be run as root"
    exit 1
fi

# check arguments
NUM_ARGS=$#
if [ ${NUM_ARGS} -ne 2 ] ; then
    echo "Usage: ${SCRIPT} END_HOUR END_MINUTE"
    exit 1
fi
END_HR=$1
END_MN=$2

# calculate time to end, in seconds past the epoch
SEC_THEN=`date --date="$END_HR:$END_MN:00" +%s`
if [ $SEC_THEN -le `date +%s` ] ; then
    SEC_THEN=`date --date="$END_HR:$END_MN:00 1 day" +%s`
fi

# function to set the global time to live for TIMEOUT
set_ttl()
{
    SEC_NOW=`date +%s`
    TTL=`expr $SEC_THEN - $SEC_NOW`
    if [ $TTL -lt 1 ] ; then
        TTL=1
    fi
}

# visit hosts, with timeout
set_ttl
echo "Time To Live is now $TTL seconds"
${TIMEOUT} -${SIGINT} ${TTL} ${VISITOR} ${STATE} ${BACKUPS} ${XML_FILES} 2>&1
