#!/bin/sh

# nightly.sh - Perform a command as singleton, logging and emailing its output
#              Rotates logfiles
#              Make sure paths are right for your specific system
#              Written by jwiggins 3/14/2012

# paths on this system
BASENAME="/usr/bin/basename"
MAIL="/usr/bin/mail"

COMMAND=`${BASENAME} $1`

LOG_DIR="/var/log/inveneo"
LOG_FILE="${LOG_DIR}/${COMMAND}.log"
TMPLOG="/tmp/${COMMAND}.log"
PIDFILE="/tmp/${COMMAND}.pid"

SUBJECT="`hostname`:${COMMAND}"
MAILTO="nightly@inveneo.org"

# rotate log files
mkdir -p ${LOG_DIR}
if [ -e ${LOG_FILE} ] ; then
    mv -f ${LOG_FILE}.5 ${LOG_FILE}.6 > /dev/null
    mv -f ${LOG_FILE}.4 ${LOG_FILE}.5 > /dev/null
    mv -f ${LOG_FILE}.3 ${LOG_FILE}.4 > /dev/null
    mv -f ${LOG_FILE}.2 ${LOG_FILE}.3 > /dev/null
    mv -f ${LOG_FILE}.1 ${LOG_FILE}.2 > /dev/null
    mv -f ${LOG_FILE}   ${LOG_FILE}.1 > /dev/null
fi

# start logging
echo "${COMMAND} starting at `date`" 2>&1 >> ${LOG_FILE}

# a simple way to usually keep two instances from running (has race condition)
if [ -e ${PIDFILE} ] && kill -0 `cat ${PIDFILE}`; then
    echo "${COMMAND} is already running: exiting" 2>&1 >> ${LOG_FILE}
    exit 1
fi

# make sure the lockfile is removed if we blow up or exit, and take it
trap "rm -f ${PIDFILE}; exit" INT TERM EXIT
echo $$ > ${PIDFILE}

# execute the command as passed in
$* 2>&1 >> ${LOG_FILE}

# attempt to send email report (append any output to logfile)
echo "${COMMAND} sending report at `date`" 2>&1 >> ${LOG_FILE}
cat ${LOG_FILE} | ${MAIL} -s"${SUBJECT}" ${MAILTO} 2>&1 > ${TMPLOG}
cat ${TMPLOG} >> ${LOG_FILE}
rm -f ${TMPLOG}

echo "${COMMAND} finishing at `date`" 2>&1 >> ${LOG_FILE}
