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
""" Test class PriorityDict. """
from diplomacy.utils.priority_dict import PriorityDict
from diplomacy.utils.tests.test_common import assert_equals

def test_priority_dict():
    """ Test Heap class PriorityDict. """

    for unordered_list in [
            [464, 21, 43453, 211, 324, 321, 102, 1211, 14, 875, 1, 33444, 22],
            'once upon a time in West'.split(),
            'This is a sentence with many words like panthera, lion, tiger, cat or cheetah!'.split()
    ]:
        expected_ordered_set = list(sorted(set(unordered_list)))
        computed_sorted_list = []
        priority_dict = PriorityDict()
        for element in unordered_list:
            priority_dict[element] = element
        while priority_dict:
            value, key = priority_dict.smallest()
            computed_sorted_list.append(value)
            del priority_dict[key]
        assert_equals(expected_ordered_set, computed_sorted_list)

def test_item_getter_setter_deletion():
    """ Test PriorityDict item setter/getter/deletion. """

    priority_dict = PriorityDict()
    priority_dict['a'] = 12
    priority_dict['f'] = 9
    priority_dict['b'] = 23
    assert list(priority_dict.keys()) == ['f', 'a', 'b']
    assert priority_dict['a'] == 12
    assert priority_dict['f'] == 9
    assert priority_dict['b'] == 23
    priority_dict['e'] = -1
    priority_dict['a'] = 8
    del priority_dict['b']
    assert list(priority_dict.keys()) == ['e', 'a', 'f']
    assert list(priority_dict.values()) == [-1, 8, 9]

def test_iterations():
    """ test iterations:
        - for key in priority_dict
        - priority_dict.keys()
        - priority_dict.values()
        - priority_dict.items()
    """
    priorities = [464, 21, 43453, 211, 324, 321, 102, 1211, 14, 875, 1, 33444, 22]

    # Build priority dict.
    priority_dict = PriorityDict()
    for priority in priorities:
        priority_dict['value of %s' % priority] = priority

    # Build expected priorities and keys.
    expected_sorted_priorities = list(sorted(priorities))
    expected_sorted_keys = ['value of %s' % priority for priority in sorted(priorities)]

    # Iterate on priority dict.
    computed_sorted_priorities = [priority_dict[key] for key in priority_dict]
    # Iterate on priority dict keys.
    sorted_priorities_from_key = [priority_dict[key] for key in priority_dict.keys()]
    # Iterate on priority dict values.
    sorted_priorities_from_values = list(priority_dict.values())
    # Iterate on priority dict items.
    priority_dict_items = list(priority_dict.items())
    # Get priority dict keys.
    priority_dict_keys = list(priority_dict.keys())
    # Get priority dict keys from items (to validate items).
    priority_dict_keys_from_items = [item[0] for item in priority_dict_items]
    # Get priority dict values from items (to validate items).
    priority_dict_values_from_items = [item[1] for item in priority_dict_items]

    for expected, computed in [
            (expected_sorted_priorities, computed_sorted_priorities),
            (expected_sorted_priorities, sorted_priorities_from_key),
            (expected_sorted_priorities, sorted_priorities_from_values),
            (expected_sorted_priorities, priority_dict_values_from_items),
            (expected_sorted_keys, priority_dict_keys_from_items),
            (expected_sorted_keys, priority_dict_keys),
    ]:
        assert_equals(expected, computed)

    # Priority dict should have not been modified.
    assert_equals(len(priorities), len(priority_dict))
    assert all(key in priority_dict for key in expected_sorted_keys)
