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
""" Sorted set implementation. """
import bisect
from copy import copy

from diplomacy.utils import exceptions
from diplomacy.utils.common import is_sequence

class SortedSet:
    """ Sorted set (sorted values, each value appears once). """
    __slots__ = ('__type', '__list')

    def __init__(self, element_type, content=()):
        """ Initialize a typed sorted set.

            :param element_type: Expected type for values.
            :param content: (optional) Sequence of values to initialize sorted set with.
        """
        if not is_sequence(content):
            raise exceptions.TypeException('sequence', type(content))
        self.__type = element_type
        self.__list = []
        for element in content:
            self.add(element)

    @staticmethod
    def builder(element_type):
        """ Return a function to build sorted sets from content (sequence of values).
            Returned function expects a content parameter like SortedSet initializer.

            .. code-block:: python

                builder_fn = SortedSet.builder(str)
                my_sorted_set = builder_fn(['c', '3', 'p', '0'])

            :param element_type: expected type for sorted set values.
            :return: callable
        """
        return lambda iterable: SortedSet(element_type, iterable)

    @property
    def element_type(self):
        """ Get values type. """
        return self.__type

    def __str__(self):
        """ String representation """
        return 'SortedSet(%s, %s)' % (self.__type.__name__, self.__list)

    def __len__(self):
        """ Returns len of SortedSet """
        return len(self.__list)

    def __eq__(self, other):
        """ Determines if 2 SortedSets are equal """
        assert isinstance(other, SortedSet)
        return (self.element_type is other.element_type
                and len(self) == len(other)
                and all(a == b for a, b in zip(self, other)))

    def __getitem__(self, index):
        """ Returns the item at the position index """
        return copy(self.__list[index])

    def __iter__(self):
        """ Returns an iterator """
        return self.__list.__iter__()

    def __reversed__(self):
        """ Return reversed view of internal list. """
        return reversed(self.__list)

    def __contains__(self, element):
        """ Determines if the element is in the SortedSet """
        assert isinstance(element, self.__type)
        if self.__list:
            position = bisect.bisect_left(self.__list, element)
            return position != len(self.__list) and self.__list[position] == element
        return False

    def add(self, element):
        """ Add an element. """
        assert isinstance(element, self.__type)
        if self.__list:
            best_position = bisect.bisect_left(self.__list, element)
            if best_position == len(self.__list):
                self.__list.append(element)
            elif self.__list[best_position] != element:
                self.__list.insert(best_position, element)
        else:
            self.__list.append(element)
            best_position = 0
        return best_position

    def get_next_value(self, element):
        """ Get lowest value in sorted set greater than given element, or None if such values
            does not exists in the sorted set. Given element may not exists in the sorted set.
        """
        assert isinstance(element, self.__type)
        if self.__list:
            best_position = bisect.bisect_right(self.__list, element)
            if best_position != len(self.__list):
                if self.__list[best_position] != element:
                    return self.__list[best_position]
                if best_position + 1 < len(self.__list):
                    return self.__list[best_position + 1]
        return None

    def get_previous_value(self, element):
        """ Get greatest value in sorted set less the given element, or None if such value
            does not exists in the sorted set. Given element may not exists in the sorted set.
        """
        assert isinstance(element, self.__type)
        if self.__list:
            best_position = bisect.bisect_left(self.__list, element)
            if best_position == len(self.__list):
                return self.__list[len(self.__list) - 1]
            if best_position != 0:
                return self.__list[best_position - 1]
        return None

    def pop(self, index):
        """ Remove and return value at given index. """
        return self.__list.pop(index)

    def remove(self, element):
        """ Remove and return element. """
        assert isinstance(element, self.__type)
        if self.__list:
            position = bisect.bisect_left(self.__list, element)
            if position != len(self.__list) and self.__list[position] == element:
                return self.pop(position)
        return None

    def index(self, element):
        """ Return index of element in the set, or None if element is not in the set. """
        assert isinstance(element, self.__type)
        if self.__list:
            position = bisect.bisect_left(self.__list, element)
            if position != len(self.__list) and self.__list[position] == element:
                return position
        return None

    def clear(self):
        """ Remove all items from set. """
        self.__list.clear()
