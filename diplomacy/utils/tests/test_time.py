# ==============================================================================
# Copyright (C) 2019 - Philip Paquette, Steven Bocco
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
""" Tests cases for time function"""
from diplomacy.utils import str_to_seconds, next_time_at, trunc_time

def test_str_to_seconds():
    """ Tests for str_to_seconds """
    assert str_to_seconds('1W') == 604800
    assert str_to_seconds('1D') == 86400
    assert str_to_seconds('1H') == 3600
    assert str_to_seconds('1M') == 60
    assert str_to_seconds('1S') == 1
    assert str_to_seconds('1') == 1
    assert str_to_seconds(1) == 1

    assert str_to_seconds('10W') == 10 * 604800
    assert str_to_seconds('10D') == 10 * 86400
    assert str_to_seconds('10H') == 10 * 3600
    assert str_to_seconds('10M') == 10 * 60
    assert str_to_seconds('10S') == 10 * 1
    assert str_to_seconds('10') == 10 * 1
    assert str_to_seconds(10) == 10 * 1

    assert str_to_seconds('1W2D3H4M5S') == 1 * 604800 + 2 * 86400 + 3 * 3600 + 4 * 60 + 5
    assert str_to_seconds('1W2D3H4M5') == 1 * 604800 + 2 * 86400 + 3 * 3600 + 4 * 60 + 5
    assert str_to_seconds('11W12D13H14M15S') == 11 * 604800 + 12 * 86400 + 13 * 3600 + 14 * 60 + 15
    assert str_to_seconds('11W12D13H14M15') == 11 * 604800 + 12 * 86400 + 13 * 3600 + 14 * 60 + 15

def test_trunc_time():
    """ Tests for trunc_time """
    # 1498746123 = Thursday, June 29, 2017 10:22:03 AM GMT-04:00 DST
    assert trunc_time(1498746123, '1M', 'America/Montreal') == 1498746180       # 10:23
    assert trunc_time(1498746123, '5M', 'America/Montreal') == 1498746300       # 10:25
    assert trunc_time(1498746123, '10M', 'America/Montreal') == 1498746600      # 10:30
    assert trunc_time(1498746123, '15M', 'America/Montreal') == 1498746600      # 10:30
    assert trunc_time(1498746123, '20M', 'America/Montreal') == 1498747200      # 10:40
    assert trunc_time(1498746123, '25M', 'America/Montreal') == 1498746300      # 10:25

    # 1498731723 = Thursday, June 29, 2017 10:22:03 AM GMT
    assert trunc_time(1498731723, '1M', 'GMT') == 1498731780       # 10:23
    assert trunc_time(1498731723, '5M', 'GMT') == 1498731900       # 10:25
    assert trunc_time(1498731723, '10M', 'GMT') == 1498732200      # 10:30
    assert trunc_time(1498731723, '15M', 'GMT') == 1498732200      # 10:30
    assert trunc_time(1498731723, '20M', 'GMT') == 1498732800      # 10:40
    assert trunc_time(1498731723, '25M', 'GMT') == 1498731900      # 10:25

def test_next_time_at():
    """ Tests for next_time_at """
    # 1498746123 = Thursday, June 29, 2017 10:22:03 AM GMT-04:00 DST
    assert next_time_at(1498746123, '10:23', 'America/Montreal') == 1498746180      # 10:23
    assert next_time_at(1498746123, '10:25', 'America/Montreal') == 1498746300      # 10:25
    assert next_time_at(1498746123, '10:30', 'America/Montreal') == 1498746600      # 10:30
    assert next_time_at(1498746123, '10:40', 'America/Montreal') == 1498747200      # 10:40
    assert next_time_at(1498746123, '16:40', 'America/Montreal') == 1498768800      # 16:40
    assert next_time_at(1498746123, '6:20', 'America/Montreal') == 1498818000       # 6:20 (Next day)

    # 1498731723 = Thursday, June 29, 2017 10:22:03 AM GMT
    assert next_time_at(1498731723, '10:23', 'GMT') == 1498731780      # 10:23
    assert next_time_at(1498731723, '10:25', 'GMT') == 1498731900      # 10:25
    assert next_time_at(1498731723, '10:30', 'GMT') == 1498732200      # 10:30
    assert next_time_at(1498731723, '10:40', 'GMT') == 1498732800      # 10:40
    assert next_time_at(1498731723, '16:40', 'GMT') == 1498754400      # 16:40
    assert next_time_at(1498731723, '6:20', 'GMT') == 1498803600       # 6:20 (Next day)
