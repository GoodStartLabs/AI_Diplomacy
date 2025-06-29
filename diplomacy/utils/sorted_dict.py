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
""" Helper class to provide a dict with sorted keys. """
from diplomacy.utils.common import is_dictionary
from diplomacy.utils.sorted_set import SortedSet

class SortedDict:
    """ Dict with sorted keys. """
    __slots__ = ['__val_type', '__keys', '__couples']

    def __init__(self, key_type, val_type, kwargs=None):
        """ Initialize a typed SortedDict.

            :param key_type: expected type for keys.
            :param val_type: expected type for values.
            :param kwargs: (optional) dictionary-like object: initial values for sorted dict.
        """
        self.__val_type = val_type
        self.__keys = SortedSet(key_type)
        self.__couples = {}
        if kwargs is not None:
            assert is_dictionary(kwargs)
            for key, value in kwargs.items():
                self.put(key, value)

    @staticmethod
    def builder(key_type, val_type):
        """ Return a function to build sorted dicts from a dictionary-like object.
            Returned function expects a dictionary parameter (an object with method items()).

            .. code-block:: python

                builder_fn = SortedDict.builder(str, int)
                my_sorted_dict = builder_fn({'a': 1, 'b': 2})

            :param key_type: expected type for keys.
            :param val_type: expected type for values.
            :return: callable
        """
        return lambda dictionary: SortedDict(key_type, val_type, dictionary)

    @property
    def key_type(self):
        """ Get key type. """
        return self.__keys.element_type

    @property
    def val_type(self):
        """ Get value type. """
        return self.__val_type

    def __str__(self):
        return 'SortedDict{%s}' % ', '.join('%s:%s' % (k, self.__couples[k]) for k in self.__keys)

    def __bool__(self):
        return bool(self.__keys)

    def __len__(self):
        return len(self.__keys)

    def __eq__(self, other):
        """ Return True if self and other are equal.
            Note that self and other must also have same key and value types.
        """
        assert isinstance(other, SortedDict)
        return (self.key_type is other.key_type
                and self.val_type is other.val_type
                and len(self) == len(other)
                and all(key in other and self[key] == other[key] for key in self.__keys))

    def __getitem__(self, key):
        return self.__couples[key]

    def __setitem__(self, key, value):
        self.put(key, value)

    def __delitem__(self, key):
        self.remove(key)

    def __iter__(self):
        return self.__keys.__iter__()

    def __contains__(self, key):
        return key in self.__couples

    def get(self, key, default=None):
        """ Return value associated with key, or default value if key not found. """
        return self.__couples.get(key, default)

    def put(self, key, value):
        """ Add a key with a value to the dict. """
        if not isinstance(value, self.__val_type):
            raise TypeError('Expected value type %s, got %s' % (self.__val_type, type(value)))
        if key not in self.__keys:
            self.__keys.add(key)
        self.__couples[key] = value

    def remove(self, key):
        """ Pop (remove and return) value associated with given key, or None if key not found. """
        if key in self.__couples:
            self.__keys.remove(key)
        return self.__couples.pop(key, None)

    def first_key(self):
        """ Get the lowest key from the dict. """
        return self.__keys[0]

    def first_value(self):
        """ Get the value associated to lowest key in the dict. """
        return self.__couples[self.__keys[0]]

    def last_key(self):
        """ Get the highest key from the dict. """
        return self.__keys[-1]

    def last_value(self):
        """ Get the value associated to highest key in the dict. """
        return self.__couples[self.__keys[-1]]

    def last_item(self):
        """ Get the item (key-value pair) for the highest key in the dict. """
        return self.__keys[-1], self.__couples[self.__keys[-1]]

    def keys(self):
        """ Get an iterator to the keys in the dict. """
        return iter(self.__keys)

    def values(self):
        """ Get an iterator to the values in the dict. """
        return (self.__couples[k] for k in self.__keys)

    def reversed_values(self):
        """ Get an iterator to the values in the dict in reversed order or keys. """
        return (self.__couples[k] for k in reversed(self.__keys))

    def items(self):
        """ Get an iterator to the items in the dict. """
        return ((k, self.__couples[k]) for k in self.__keys)

    def reversed_items(self):
        """ Get an iterator to the items in the dict in reversed order of keys. """
        return ((k, self.__couples[k]) for k in reversed(self.__keys))

    def sub_keys(self, key_from=None, key_to=None):
        """ Return list of keys between key_from and key_to (both bounds included). """
        position_from, position_to = self._get_keys_interval(key_from, key_to)
        return self.__keys[position_from:(position_to + 1)]

    def sub(self, key_from=None, key_to=None):
        """ Return a list of values associated to keys between key_from and key_to
            (both bounds included).

            - If key_from is None, lowest key in dict is used.
            - If key_to is None, greatest key in dict is used.
            - If key_from is not in dict, lowest key in dict greater than key_from is used.
            - If key_to is not in dict, greatest key in dict less than key_to is used.

            - If dict is empty, return empty list.
            - With keys (None, None) return a copy of all values.
            - With keys (None, key_to), return values from first to the one associated to key_to.
            - With keys (key_from, None), return values from the one associated to key_from to the last value.

            :param key_from: start key
            :param key_to: end key
            :return: list: values in closed keys interval [key_from; key_to]
        """
        position_from, position_to = self._get_keys_interval(key_from, key_to)
        return [self.__couples[k] for k in self.__keys[position_from:(position_to + 1)]]

    def remove_sub(self, key_from=None, key_to=None):
        """ Remove values associated to keys between key_from and key_to (both bounds included).

            See sub() doc about key_from and key_to.

            :param key_from: start key
            :param key_to: end key
            :return: nothing
        """
        position_from, position_to = self._get_keys_interval(key_from, key_to)
        keys_to_remove = self.__keys[position_from:(position_to + 1)]
        for key in keys_to_remove:
            self.remove(key)

    def key_from_index(self, index):
        """ Return key matching given position in sorted dict, or None for invalid position. """
        return self.__keys[index] if -len(self.__keys) <= index < len(self.__keys) else None

    def get_previous_key(self, key):
        """ Return greatest key lower than given key, or None if not exists. """
        return self.__keys.get_previous_value(key)

    def get_next_key(self, key):
        """ Return smallest key greater then given key, or None if not exists. """
        return self.__keys.get_next_value(key)

    def _get_keys_interval(self, key_from, key_to):
        """ Get a couple of internal key positions (index of key_from, index of key_to) allowing
            to easily retrieve values in closed interval [index of key_from; index of key_to]
            corresponding to Python slice [index of key_from : (index of key_to + 1)]

            - If dict is empty, return (0, -1), so that python slice [0 : -1 + 1] corresponds to empty interval.
            - If key_from is None, lowest key in dict is used.
            - If key_to is None, greatest key in dict is used.
            - If key_from is not in dict, lowest key in dict greater than key_from is used.
            - If key_to is not in dict, greatest key in dict less than key_to is used.

            - With keys (None, None), we get interval of all values.
            - With keys (key_from, None), we get interval for values from key_from to the last key.
            - With keys (None, key_to), we get interval for values from the first key to key_to.

            :param key_from: start key
            :param key_to: end key
            :return: (int, int): couple of integers: (index of key_from, index of key_to).
        """
        if not self:
            return 0, -1
        if key_from is not None and key_from not in self.__couples:
            key_from = self.__keys.get_next_value(key_from)
            if key_from is None:
                return 0, -1
        if key_to is not None and key_to not in self.__couples:
            key_to = self.__keys.get_previous_value(key_to)
            if key_to is None:
                return 0, -1
        if key_from is None and key_to is None:
            key_from = self.first_key()
            key_to = self.last_key()
        elif key_from is not None and key_to is None:
            key_to = self.last_key()
        elif key_from is None and key_to is not None:
            key_from = self.first_key()
        if key_from > key_to:
            raise IndexError('expected key_from <= key_to (%s vs %s)' % (key_from, key_to))
        position_from = self.__keys.index(key_from)
        position_to = self.__keys.index(key_to)
        assert position_from is not None and position_to is not None
        return position_from, position_to

    def clear(self):
        """ Remove all items from dict. """
        self.__couples.clear()
        self.__keys.clear()

    def fill(self, dct):
        """ Add given dict to this sorted dict. """
        if dct:
            assert is_dictionary(dct)
            for key, value in dct.items():
                self.put(key, value)

    def copy(self):
        """ Return a copy of this sorted dict. """
        return SortedDict(self.__keys.element_type, self.__val_type, self.__couples)
