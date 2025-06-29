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
""" Test class SortedSet. """
from diplomacy.utils import common
from diplomacy.utils.sorted_set import SortedSet
from diplomacy.utils.tests.test_common import assert_equals

def test_init_bool_and_len():
    """ Test SortedSet initialization, length and conversion to boolean. """

    sorted_set = SortedSet(int)
    assert not sorted_set
    sorted_set = SortedSet(int, (2, 4, 99))
    assert sorted_set
    assert len(sorted_set) == 3

def test_builder_and_property():
    """ Test SortedSet builder and property element_type. """

    builder_float = SortedSet.builder(float)
    sorted_set = builder_float((2.5, 2.7, 2.9))
    assert isinstance(sorted_set, SortedSet) and sorted_set.element_type is float

def test_item_add_get_and_contains():
    """ Test SortedSet methods add(), __getitem__(), and __contains__(). """

    expected_values = ['cat', 'lion', 'panthera', 'serval', 'tiger']
    sorted_set = SortedSet(str, ('lion', 'tiger'))
    # Test setter.
    sorted_set.add('panthera')
    sorted_set.add('cat')
    sorted_set.add('serval')
    # Test __contains__.
    assert 'lions' not in sorted_set
    assert all(key in sorted_set for key in expected_values)
    # Test getter.
    assert sorted_set[0] == 'cat'
    assert sorted_set[1] == 'lion'
    assert sorted_set[2] == 'panthera'
    assert sorted_set[3] == 'serval'
    assert sorted_set[4] == 'tiger'
    # Test add then getter.
    sorted_set.add('onca')
    assert sorted_set[1] == 'lion'
    assert sorted_set[2] == 'onca'
    assert sorted_set[3] == 'panthera'

def test_pop_and_remove():
    """ Test SortedSet methods remove() and pop(). """

    sorted_set = SortedSet(str, ('lion', 'tiger', 'panthera', 'cat', 'serval'))
    assert len(sorted_set) == 5
    assert 'serval' in sorted_set
    sorted_set.remove('serval')
    assert len(sorted_set) == 4
    assert 'serval' not in sorted_set
    assert sorted_set.remove('tiger') == 'tiger'
    assert len(sorted_set) == 3
    assert 'tiger' not in sorted_set
    assert sorted_set.remove('tiger') is None
    assert sorted_set.remove('key not in set') is None
    index_of_panthera = sorted_set.index('panthera')
    assert index_of_panthera == 2
    assert sorted_set.pop(index_of_panthera) == 'panthera'
    assert len(sorted_set) == 2
    assert 'panthera' not in sorted_set
    assert 'cat' in sorted_set
    assert 'lion' in sorted_set

def test_iteration():
    """ Test SortedSet iteration. """

    expected_sorted_values = ['cat', 'lion', 'panthera', 'serval', 'tiger']
    sorted_set = SortedSet(str, ('lion', 'tiger', 'panthera', 'cat', 'serval'))
    computed_sorted_values = [key for key in sorted_set]
    assert_equals(expected_sorted_values, computed_sorted_values)

def test_equality():
    """ Test SortedSet equality. """

    empty_sorted_set_float = SortedSet(float)
    empty_sorted_set_int = SortedSet(int)
    another_empty_sorted_set_int = SortedSet(int)
    sorted_set_float_1 = SortedSet(float, (2.5, 3.3, -5.7))
    sorted_set_float_2 = SortedSet(float, (2.5, 3.3, -5.7))
    sorted_set_float_3 = SortedSet(float, (2.5, 3.3, 5.7))
    assert empty_sorted_set_float != empty_sorted_set_int
    assert empty_sorted_set_int == another_empty_sorted_set_int
    assert sorted_set_float_1 == sorted_set_float_2
    assert sorted_set_float_1 != sorted_set_float_3

def test_getters_around_values():
    """Test SortedSet methods get_next_value() and get_previous_value()."""

    sorted_set = SortedSet(int, (2, 5, 1, 9, 4, 5, 20, 0, 6, 17, 8, 3, 7, 0, 4))
    expected = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 20)
    assert sorted_set
    assert len(sorted_set) == len(expected)
    assert all(expected[i] == sorted_set[i] for i in range(len(expected)))
    assert all(e in sorted_set for e in expected)
    assert sorted_set.get_next_value(0) == 1
    assert sorted_set.get_next_value(5) == 6
    assert sorted_set.get_next_value(9) == 17
    assert sorted_set.get_next_value(-1) == 0
    assert sorted_set.get_next_value(20) is None
    assert sorted_set.get_previous_value(0) is None
    assert sorted_set.get_previous_value(17) == 9
    assert sorted_set.get_previous_value(20) == 17
    assert sorted_set.get_previous_value(1) == 0
    assert sorted_set.get_previous_value(6) == 5

    assert sorted_set.get_next_value(3) == 4
    assert sorted_set.get_next_value(4) == 5
    assert sorted_set.get_next_value(7) == 8
    assert sorted_set.get_next_value(8) == 9
    assert sorted_set.get_previous_value(5) == 4
    assert sorted_set.get_previous_value(4) == 3
    assert sorted_set.get_previous_value(9) == 8
    assert sorted_set.get_previous_value(8) == 7
    sorted_set.remove(8)
    assert len(sorted_set) == len(expected) - 1
    assert 8 not in sorted_set
    sorted_set.remove(4)
    assert len(sorted_set) == len(expected) - 2
    assert 4 not in sorted_set
    assert sorted_set.get_next_value(3) == 5
    assert sorted_set.get_next_value(4) == 5
    assert sorted_set.get_next_value(7) == 9
    assert sorted_set.get_next_value(8) == 9
    assert sorted_set.get_previous_value(5) == 3
    assert sorted_set.get_previous_value(4) == 3
    assert sorted_set.get_previous_value(9) == 7
    assert sorted_set.get_previous_value(8) == 7

def test_index():
    """ Test SortedSet method index(). """

    sorted_set = SortedSet(int, (2, 5, 1, 9, 4, 5, 20, 0, 6, 17, 8, 3, 7, 0, 4))
    sorted_set.remove(8)
    sorted_set.remove(4)
    index_of_2 = sorted_set.index(2)
    index_of_17 = sorted_set.index(17)
    assert index_of_2 == 2
    assert sorted_set.index(4) is None
    assert sorted_set.index(8) is None
    assert index_of_17 == len(sorted_set) - 2
    assert sorted_set.pop(index_of_2) == 2

def test_common_utils_with_sorted_set():
    """Check sorted set with is_sequence() and is_dictionary()."""
    assert common.is_sequence(SortedSet(int, (1, 2, 3)))
    assert common.is_sequence(SortedSet(int))
    assert not common.is_dictionary(SortedSet(int, (1, 2, 3)))
    assert not common.is_dictionary(SortedSet(int))
