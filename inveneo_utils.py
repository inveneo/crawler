#!/usr/bin/env python

# inveneo_utils.py

"""Inveneo's utility functions.

Written by jwiggins@inveneo.org 2011-2012
"""

import math
import subprocess
import ipaddr
import inveneo_const

MILES_PER_KM = 0.621371192

##### Networking #####

def host_is_pingable(host):
    ret = subprocess.call("ping -n -c 1 %s" % host,
                          shell=True,
                          stdout=open('/dev/null', 'w'),
                          stderr=subprocess.STDOUT)
    return (ret == 0)

##### Geometry #####

def haversine(lat1, lon1, lat2, lon2):
    '''use haversine formula to compute distance (km) between sites'''
    # code from http://www.movable-type.co.uk/scripts/latlong.html
    R = 6371.0 # radius of Earth in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    #return d * MILES_PER_KM
    return d

def spherical(lat1, lon1, lat2, lon2):
    '''use spherical law of cosines to compute distance (km) between sites'''
    # code from http://www.movable-type.co.uk/scripts/latlong.html
    try:
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)
    except TypeError:
        return '1.1' # ???
    R = 6371.0 # radius of Earth in km
    d = math.acos(math.sin(lat1) * math.sin(lat2) + \
                  math.cos(lat1) * math.cos(lat2) * math.cos(lon2-lon1)) * R
    #return d * MILES_PER_KM
    return d

def initial_bearing(lat1, lon1, lat2, lon2):
    '''compute initial bearing (true degrees) from site1 toward site2'''
    # code from http://www.movable-type.co.uk/scripts/latlong.html
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - \
        math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    return math.degrees(math.atan2(y, x))

##### User Input #####

def default_input(prompt, default):
    '''take user input and return it, or a default value if no input'''
    s = raw_input('%s [%s]: ' % (prompt, default))
    if s == '': return default
    return s

def answer_yes(prompt, default):
    '''get a yes or no response from user, return as boolean'''
    return default_input(prompt, default).upper() in ['Y', 'YES']

def input_site(prompt, default):
    '''get site name from user and do some checking on it'''
    name = None
    while not name:
        name = default_input(prompt, default).upper()
        if not len(name) in [4,5]:
            print 'Site name must be four or five characters long ... try again'
            name = None
    return name

def input_possible_float(prompt, default):
    '''get a valid floating point number, or None'''
    value = None
    while not value:
        s = default_input(prompt, default)
        if s == '': break
        try:
            value = float(s)
        except ValueError:
            print 'Invalid value "%s" ... try again' % s
            value = None
    return value

def input_lat_lon(latPrompt, lonPrompt):
    '''get a lat/lon pair from user and do some checking on it'''
    lat = input_possible_float(latPrompt, '')
    if not lat: return (None, None)
    lon = input_possible_float(lonPrompt, '')
    if not lon: return (None, None)
    return (lat, lon)

def input_ipv4(prompt, default):
    '''get a valid IPv4 address or network from the user'''
    addr = None
    while not addr:
        value = default_input(prompt, default)
        octets = value.split('.')
        if len(octets) != 4:
            print 'Must have four octets: try again'
            continue
        defective = False
        for i in range(4):
            try:
                octet = int(octets[i])
                if (octet < 0) or (255 < octet):
                    print 'Octet must be in range 0..255: try again'
                    defective = True
                    break
            except ValueError:
                print 'Octet must be integer: try again'
                defective = True
                break
        if not defective: addr = value
    return addr

def input_subnet(prompt, default):
    '''get a valid IPv4 subnet from the user'''
    value = default_input(prompt, default)
    return ipaddr.IPv4Network(value)

##### Etc #####

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

##### Unit Tests #####

if __name__ == '__main__':

    if host_is_pingable('localhost'): print 'You are pingable'
    if not host_is_pingable('10.0.0.0'): print '10.0.0.0 is not pingable'

