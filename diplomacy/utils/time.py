# ==============================================================================
# Copyright (C) 2019 - Philip Paquette
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU Affero General Public License as published by the Free
#  Software Foundation, either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
#  details.
#
#  You should have received a copy of the GNU Affero General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
""" Time functions
    - Contains generic time functions (e.g. to calculate deadlines)
"""
import calendar
import datetime
import math
import pytz

def str_to_seconds(offset_str):
    """ Converts a time in format 00W00D00H00M00S in number of seconds

        :param offset_str: The string to convert (e.g. '20D')
        :return: Its equivalent in seconds = 1728000
    """
    mult = {'W': 7 * 24 * 60 * 60, 'D': 24 * 60 * 60, 'H': 60 * 60, 'M': 60, 'S': 1, ' ': 1}
    buffer = current_sum = 0
    offset_str = str(offset_str)

    # Adding digits to buffer, when a character is found,
    # multiply it with buffer and increase the current_sum
    for char in offset_str:
        if char.isdigit():
            buffer = buffer * 10 + int(char)
        elif char.upper() in mult:
            current_sum += buffer * mult[char.upper()]
            buffer = 0
        else:
            buffer = 0
    current_sum += buffer

    return current_sum

def trunc_time(timestamp, trunc_interval, time_zone='GMT'):
    """  Truncates time at a specific interval (e.g. 20M) (i.e. Rounds to the next :20, :40, :60)

        :param timestamp: The unix epoch to truncate (e.g. 1498746120)
        :param trunc_interval: The truncation interval (e.g. 60*60 or '1H')
        :param time_zone: The time to use for conversion (defaults to GMT otherwise)
        :return: A timestamp truncated to the nearest (future) interval
    """
    midnight_ts = calendar.timegm(datetime.datetime.combine(datetime.date.today(), datetime.time.min).utctimetuple())
    midnight_offset = (timestamp - midnight_ts) % (24*3600)

    dtime = datetime.datetime.fromtimestamp(timestamp, pytz.timezone(time_zone))
    tz_offset = dtime.utcoffset().total_seconds()
    interval = str_to_seconds(trunc_interval)
    trunc_offset = math.ceil((midnight_offset + tz_offset) / interval) * interval

    trunc_ts = timestamp - midnight_offset + trunc_offset - tz_offset
    return int(trunc_ts)

def next_time_at(timestamp, time_at, time_zone='GMT'):
    """ Returns the next timestamp at a specific 'hh:mm'

        :param timestamp: The unix timestamp to convert
        :param time_at: The next 'hh:mm' to have the time rounded to, or 0 to skip
        :param time_zone: The time to use for conversion (defaults to GMT otherwise)
        :return: A timestamp truncated to the nearest (future) hh:mm
    """
    if not time_at:
        return timestamp

    midnight_ts = calendar.timegm(datetime.datetime.combine(datetime.date.today(), datetime.time.min).utctimetuple())
    midnight_offset = (timestamp - midnight_ts) % (24*3600)

    dtime = datetime.datetime.fromtimestamp(timestamp, pytz.timezone(time_zone))
    tz_offset = dtime.utcoffset().total_seconds()
    trunc_interval = '%dH%dM' % (int(time_at.split(':')[0]), int(time_at.split(':')[1])) if ':' in time_at else time_at
    interval = str_to_seconds(trunc_interval)
    at_offset = (-midnight_offset + interval - tz_offset) % (24 * 3600)
    at_ts = timestamp + at_offset
    return int(at_ts)
