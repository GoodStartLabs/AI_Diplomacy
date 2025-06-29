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
""" SubjectSplit
    - Contains utils to retrieve splitted subjects fields
"""
from abc import ABCMeta, abstractmethod


class AbstractStringSplitter(metaclass=ABCMeta):
    """ Breaks a string into its components - Generic class """
    def __init__(self, string, length):
        """ Constructor

            :param string: the string to split
            :param length: the maximum length of the split
        """
        self._input_str = string if isinstance(string, str) else ' '.join(string)
        self._parts = [None] * length
        self._last_index = 0

        self._split()

    def __len__(self):
        """ Define the length of the split """
        return self._last_index

    @property
    def input_str(self):
        """ Return the input string used to build the split """
        return self._input_str

    @property
    def parts(self):
        """ Return the array of the parts after split """
        return self._parts[:self._last_index]

    def join(self):
        """ Return the joined parts """
        return ' '.join(str(self._parts[:self._last_index]))

    @abstractmethod
    def _split(self):
        """ Build the subject split using it's _input_str """
        raise NotImplementedError()

class OrderSplitter(AbstractStringSplitter):
    """ Splits an order into its components """
    def __init__(self, string):
        """ Constructor

            :param string: the string to split
        """
        self._unit_index = None
        self._order_type_index = None
        self._supported_unit_index = None
        self._support_order_type_index = None
        self._destination_index = None
        self._via_flag_index = None

        super(OrderSplitter, self).__init__(string, 6)

    @property
    def unit(self):
        """ Return the unit of the order """
        return self._parts[self._unit_index] if self._unit_index is not None else None

    @unit.setter
    def unit(self, value):
        """ Set the unit of the order and define the index of the part if not already set """
        if self._unit_index is None:
            self._unit_index = self._last_index
            self._last_index += 1
        self._parts[self._unit_index] = value

    @property
    def order_type(self):
        """ Return the order_type """
        return self._parts[self._order_type_index] if self._order_type_index is not None else None

    @order_type.setter
    def order_type(self, value):
        """ Set the order_type and define the index of the part if not already set """
        if self._order_type_index is None:
            self._order_type_index = self._last_index
            self._last_index += 1
        self._parts[self._order_type_index] = value

    @property
    def supported_unit(self):
        """ Return the supported unit of the order """
        return self._parts[self._supported_unit_index] if self._supported_unit_index is not None else None

    @supported_unit.setter
    def supported_unit(self, value):
        """ Set the supported unit of the order and define the index of the part if not already set """
        if self._supported_unit_index is None:
            self._supported_unit_index = self._last_index
            self._last_index += 1
        self._parts[self._supported_unit_index] = value

    @property
    def support_order_type(self):
        """ Return the support order type of the order """
        return self._parts[self._support_order_type_index] if self._support_order_type_index is not None else None

    @support_order_type.setter
    def support_order_type(self, value):
        """ Set the support order_type of the order and define the index of the part if not already set """
        if self._support_order_type_index is None:
            self._support_order_type_index = self._last_index
            self._last_index += 1
        self._parts[self._support_order_type_index] = value

    @property
    def destination(self):
        """ Return the destination of the order """
        return self._parts[self._destination_index] if self._destination_index is not None else None

    @destination.setter
    def destination(self, value):
        """ Set the destination of the order and define the index of the part if not already set """
        if self._destination_index is None:
            self._destination_index = self._last_index
            self._last_index += 1
        self._parts[self._destination_index] = value

    @property
    def via_flag(self):
        """ Return the via_flag keyword of the order """
        return self._parts[self._via_flag_index] if self._via_flag_index is not None else None

    @via_flag.setter
    def via_flag(self, value):
        """ Set the via_flag of the order and define the index of the part if not already set """
        if self._via_flag_index is None:
            self._via_flag_index = self._last_index
            self._last_index += 1
        self._parts[self._via_flag_index] = value

    def _split(self):
        """ Build the order split using it's _input_str """
        words = self._input_str.strip().split() if isinstance(self._input_str, str) else self._input_str

        # [WAIVE]
        if len(words) == 1:
            self.order_type = words.pop()
            return

        # [A, LON, H]
        # [F, IRI, -, MAO]
        # [A, IRI, -, MAO, VIA]
        # [A, WAL, S, F,   LON]
        # [A, WAL, S, F,   MAO, -, IRI]
        # [F, NWG, C, A,   NWY, -, EDI]
        # [A, IRO, R, MAO]
        # [A, IRO, D]
        # [A, LON, B]
        # [F, LIV, B]
        self.unit = ' '.join([words.pop(0) for _ in range(2)])
        self.order_type = words.pop(0)

        # [A, IRI, -, MAO]
        # [A, IRI, R, MAO]
        if self.order_type in '-R':
            self.destination = words.pop()

        # [A, WAL, S, F, LON]
        # [A, WAL, S, F, MAO, -, IRI]
        # [F, NWG, C, A, NWY, -, EDI]
        elif self.order_type in 'SC':
            self.supported_unit = ' '.join([words.pop(0) for i in range(2)])

            # [A, WAL, S, F, MAO, -, IRI]
            # [F, NWG, C, A, NWY, -, EDI]
            if words:
                self.support_order_type = words.pop(0)
                self.destination = words.pop(0)

        # [A, IRI, -, MAO, VIA]
        if words and words[-1] == 'VIA':
            self.via_flag = words.pop()

class PhaseSplitter(AbstractStringSplitter):
    """ Splits a phase into its components """
    def __init__(self, string):
        """ Constructor

            :param string: the string to split
        """
        self._season_index = None
        self._year_index = None
        self._phase_type_index = None

        super(PhaseSplitter, self).__init__(string, 3)

    @property
    def season(self):
        """ Return the season of the phase """
        return self._parts[self._season_index] if self._season_index is not None else None

    @season.setter
    def season(self, value):
        """ Set the season of the phase and define the index of the part if not already set """
        if self._season_index is None:
            self._season_index = self._last_index
            self._last_index += 1
        self._parts[self._season_index] = value

    @property
    def year(self):
        """ Return the year of the phase """
        return self._parts[self._year_index] if self._year_index is not None else None

    @year.setter
    def year(self, value):
        """ Set the year of the phase and define the index of the part if not already set """
        if self._year_index is None:
            self._year_index = self._last_index
            self._last_index += 1
        self._parts[self._year_index] = value

    @property
    def phase_type(self):
        """ Return the type of the phase """
        return self._parts[self._phase_type_index] if self._phase_type_index is not None else None

    @phase_type.setter
    def phase_type(self, value):
        """ Set the type of the phase and define the index of the part if not already set """
        if self._phase_type_index is None:
            self._phase_type_index = self._last_index
            self._last_index += 1
        self._parts[self._phase_type_index] = value

    def _split(self):
        """ Build the phase split using it's _input_str """
        self.season = self._input_str[0]
        self.year = int(self._input_str[1:-1])
        self.phase_type = self._input_str[-1]
