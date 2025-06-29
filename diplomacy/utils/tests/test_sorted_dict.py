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
""" Test class SortedDict. """
from diplomacy.utils import common
from diplomacy.utils.sorted_dict import SortedDict
from diplomacy.utils.tests.test_common import assert_equals

def test_init_bool_and_len():
    """ Test SortedDict initialization, length and conversion to boolean. """

    sorted_dict = SortedDict(int, str)
    assert not sorted_dict
    sorted_dict = SortedDict(int, str, {2: 'two', 4: 'four', 99: 'ninety-nine'})
    assert sorted_dict
    assert len(sorted_dict) == 3

def test_builder_and_properties():
    """ Test SortedDict builder and properties key_type and val_type. """

    builder_float_to_bool = SortedDict.builder(float, bool)
    sorted_dict = builder_float_to_bool({2.5: True, 2.7: False, 2.9: True})
    assert isinstance(sorted_dict, SortedDict) and sorted_dict.key_type is float and sorted_dict.val_type is bool

def test_items_functions():
    """ Test SortedDict item setter/getter and methods put() and __contains__(). """

    expected_keys = ['cat', 'lion', 'panthera', 'serval', 'tiger']
    sorted_dict = SortedDict(str, float, {'lion': 1.5, 'tiger': -2.7})
    # Test setter.
    sorted_dict['panthera'] = -.88
    sorted_dict['cat'] = 2223.
    # Test put().
    sorted_dict.put('serval', 39e12)
    # Test __contains__.
    assert 'lions' not in sorted_dict
    assert all(key in sorted_dict for key in expected_keys)
    # Test getter.
    assert sorted_dict['cat'] == 2223.
    assert sorted_dict['serval'] == 39e12
    # Test setter then getter.
    assert sorted_dict['lion'] == 1.5
    sorted_dict['lion'] = 2.3
    assert sorted_dict['lion'] == 2.3
    # Test get,
    assert sorted_dict.get('lions') is None
    assert sorted_dict.get('lion') == 2.3

def test_item_deletion_and_remove():
    """ Test SortedDict methods remove() and __delitem__(). """

    sorted_dict = SortedDict(str, float, {'lion': 1.5, 'tiger': -2.7, 'panthera': -.88, 'cat': 2223., 'serval': 39e12})
    assert len(sorted_dict) == 5
    assert 'serval' in sorted_dict
    sorted_dict.remove('serval')
    assert len(sorted_dict) == 4
    assert 'serval' not in sorted_dict
    removed = sorted_dict.remove('tiger')
    assert len(sorted_dict) == 3
    assert 'tiger' not in sorted_dict
    assert removed == -2.7
    assert sorted_dict.remove('tiger') is None
    assert sorted_dict.remove('key not in dict') is None
    del sorted_dict['panthera']
    assert len(sorted_dict) == 2
    assert 'panthera' not in sorted_dict
    assert 'cat' in sorted_dict
    assert 'lion' in sorted_dict

def test_iterations():
    """ Test SortedDict iterations (for key in dict, keys(), values(), items()). """

    expected_sorted_keys = ['cat', 'lion', 'panthera', 'serval', 'tiger']
    expected_sorted_values = [2223., 1.5, -.88, 39e12, -2.7]
    sorted_dict = SortedDict(str, float, {'lion': 1.5, 'tiger': -2.7, 'panthera': -.88, 'cat': 2223., 'serval': 39e12})
    computed_sorted_keys = [key for key in sorted_dict]
    computed_sorted_keys_from_keys = list(sorted_dict.keys())
    computed_sorted_values = list(sorted_dict.values())
    keys_from_items = []
    values_from_items = []
    for key, value in sorted_dict.items():
        keys_from_items.append(key)
        values_from_items.append(value)
    assert_equals(expected_sorted_keys, computed_sorted_keys)
    assert_equals(expected_sorted_keys, computed_sorted_keys_from_keys)
    assert_equals(expected_sorted_keys, keys_from_items)
    assert_equals(expected_sorted_values, values_from_items)
    assert_equals(expected_sorted_values, computed_sorted_values)

def test_bound_keys_getters():
    """ Test SortedDict methods first_key(), last_key(), last_value(), last_item(),
        get_previous_key(), get_next_key().
    """

    sorted_dict = SortedDict(str, float, {'lion': 1.5, 'tiger': -2.7})
    sorted_dict['panthera'] = -.88
    sorted_dict['cat'] = 2223.
    sorted_dict['serval'] = 39e12
    assert sorted_dict.first_key() == 'cat'
    assert sorted_dict.last_key() == 'tiger'
    assert sorted_dict.last_value() == sorted_dict['tiger'] == -2.7
    assert sorted_dict.last_item() == ('tiger', -2.7)
    assert sorted_dict.get_previous_key('cat') is None
    assert sorted_dict.get_next_key('cat') == 'lion'
    assert sorted_dict.get_previous_key('tiger') == 'serval'
    assert sorted_dict.get_next_key('tiger') is None
    assert sorted_dict.get_previous_key('panthera') == 'lion'
    assert sorted_dict.get_next_key('panthera') == 'serval'

def test_equality():
    """ Test SortedDict equality. """

    empty_sorted_dict_float_int = SortedDict(float, int)
    empty_sorted_dict_float_bool_1 = SortedDict(float, bool)
    empty_sorted_dict_float_bool_2 = SortedDict(float, bool)
    sorted_dict_float_int_1 = SortedDict(float, int, {2.5: 17, 3.3: 49, -5.7: 71})
    sorted_dict_float_int_2 = SortedDict(float, int, {2.5: 17, 3.3: 49, -5.7: 71})
    sorted_dict_float_int_3 = SortedDict(float, int, {2.5: -17, 3.3: 49, -5.7: 71})
    assert empty_sorted_dict_float_int != empty_sorted_dict_float_bool_1
    assert empty_sorted_dict_float_bool_1 == empty_sorted_dict_float_bool_2
    assert sorted_dict_float_int_1 == sorted_dict_float_int_2
    assert sorted_dict_float_int_1 != sorted_dict_float_int_3

def test_sub_and_remove_sub():
    """Test SortedDict methods sub() and remove_sub()."""

    sorted_dict = SortedDict(int, str, {k: 'value of %s' % k for k in (2, 5, 1, 9, 4, 5, 20, 0, 6, 17, 8, 3, 7, 0, 4)})
    assert sorted_dict.sub() == list(sorted_dict.values())
    assert sorted_dict.sub(-10, 4) == ['value of 0', 'value of 1', 'value of 2', 'value of 3', 'value of 4']
    assert sorted_dict.sub(15) == ['value of 17', 'value of 20']
    sorted_dict.remove_sub(-10, 4)
    assert all(k not in sorted_dict for k in (0, 1, 2, 3, 4))
    sorted_dict.remove_sub(15)
    assert all(k not in sorted_dict for k in (17, 20))

def test_is_sequence_and_is_dict():
    """Check sorted dict with is_sequence() and is_dict()."""

    assert common.is_dictionary(SortedDict(str, int, {'a': 3, 'b': -1, 'c': 12}))
    assert common.is_dictionary(SortedDict(int, float), )
    assert not common.is_sequence(SortedDict(str, str))
