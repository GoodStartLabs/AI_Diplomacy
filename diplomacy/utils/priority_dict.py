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
""" Priority Dict implementation """
import heapq

# ------------------------------------------------
# Adapted from (2018/03/14s):
# https://docs.python.org/3.6/library/heapq.html#priority-queue-implementation-notes
# Unlicensed
class PriorityDict(dict):
    """ Priority Dictionary Implementation """

    def __init__(self, **kwargs):
        """ Initialize the priority queue.

            :param kwargs: (optional) initial values for priority queue.
        """
        self.__heap = []  # Heap for entries. An entry is a triple (priority value, key, valid entry flag (boolean)).
        # Dict itself maps key to entries. We override some dict methods (see __getitem__() below)
        # to always return priority value instead of entry as dict value.
        dict.__init__(self)
        for key, value in kwargs.items():
            self[key] = value

    def __setitem__(self, key, val):
        """ Sets a key with his associated priority

            :param key: The key to set in the dictionary
            :param val: The priority to associate with the key
            :return: None
        """
        if key in self:
            del self[key]
        # Create entry with val, key and a boolean indicating that entry is valid (True).
        entry = [val, key, True]
        dict.__setitem__(self, key, entry)
        heapq.heappush(self.__heap, entry)

    def __delitem__(self, key):
        """ Removes key from dict and marks associated heap entry as invalid (False).
            Raises KeyError if not found.
        """
        entry = self.pop(key)
        entry[-1] = False

    def __getitem__(self, key):
        """ Returns priority value associated to key. Raises KeyError if key not found. """
        return dict.__getitem__(self, key)[0]

    def __iter__(self):
        """ Iterator over all keys based on their priority. """

        def iterfn():
            """ Iterator """
            copy_of_self = self.copy()
            while copy_of_self:
                _, key = copy_of_self.smallest()
                del copy_of_self[key]
                yield key

        return iterfn()

    def smallest(self):
        """ Finds the smallest item in the priority dict

            :return: A tuple of (priority, key) for the item with the smallest priority, or None if dict is empty.
        """
        while self.__heap and not self.__heap[0][-1]:
            heapq.heappop(self.__heap)
        return self.__heap[0][:2] if self.__heap else None

    def setdefault(self, key, d=None):
        """ Sets a default for a given key """
        if key not in self:
            self[key] = d
        return self[key]

    def copy(self):
        """ Return a copy of this priority dict.

            :rtype: PriorityDict
        """
        return PriorityDict(**{key: entry[0] for key, entry in dict.items(self)})

    def keys(self):
        """ Make sure keys() iterates on keys based on their priority. """
        return self.__iter__()

    def values(self):
        """ Makes sure values() iterates on priority values (instead of heap entries) from smallest to highest. """
        return (self[k] for k in self)

    def items(self):
        """ Makes sure items() values are priority values instead of heap entries. """
        return ((key, self[key]) for key in self)
