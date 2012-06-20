#!/usr/bin/env python

# crawler_utils.py

"""Crawler utility functions.

Written by jwiggins@inveneo.org 2011-2012
"""

def rough_timespan(seconds):
    """Converts time difference into English string"""
    if seconds < 120: return "%d seconds" % seconds
    minutes = int(seconds / 60)
    if minutes < 120: return "%d minutes" % minutes
    hours = int(minutes / 60)
    if hours < 48: return "%d hours" % hours
    days = int(hours / 24)
    if days < 14: return "%d days" % days
    weeks = int(days / 7)
    return "%d weeks" % weeks

if __name__ == '__main__':
    secs = 400
    print '%d seconds is roughly %s' % (secs, rough_timespan(secs))
    secs = 4000
    print '%d seconds is roughly %s' % (secs, rough_timespan(secs))
    secs = 40000
    print '%d seconds is roughly %s' % (secs, rough_timespan(secs))
    secs = 400000
    print '%d seconds is roughly %s' % (secs, rough_timespan(secs))
    secs = 4000000
    print '%d seconds is roughly %s' % (secs, rough_timespan(secs))
