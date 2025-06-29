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
""" Scheduler event describing scheduler state for a specific data. """

from diplomacy.utils.jsonable import Jsonable

class SchedulerEvent(Jsonable):
    """ Scheduler event class.

        Properties:

        - **time_unit**: unit time (in seconds) used by scheduler (time between 2 tasks checkings).
          Currently 1 second in server scheduler.
        - **time_added**: scheduler time (nb. time units) when data was added to scheduler.
        - **delay**: scheduler time (nb. time units) to wait before processing time.
        - **current_time**: current scheduler time (nb. time units).
    """
    __slots__ = ['time_unit', 'time_added', 'delay', 'current_time']
    model = {
        'time_unit': int,
        'time_added': int,
        'delay': int,
        'current_time': int
    }

    def __init__(self, **kwargs):
        self.time_unit = 0
        self.time_added = 0
        self.delay = 0
        self.current_time = 0
        super(SchedulerEvent, self).__init__(**kwargs)
