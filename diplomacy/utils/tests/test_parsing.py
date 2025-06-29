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
""" Test module parsing. """
from diplomacy.utils import exceptions, parsing
from diplomacy.utils.sorted_dict import SortedDict
from diplomacy.utils.sorted_set import SortedSet
from diplomacy.utils.tests.test_common import assert_raises
from diplomacy.utils.tests.test_jsonable import MyJsonable

class MyStringable:
    """ Example of Stringable class.
        As instances of such class may be used as dict keys, class should define a proper __hash__().
    """

    def __init__(self, value):
        self.attribute = str(value)

    def __str__(self):
        return 'MyStringable %s' % self.attribute

    def __hash__(self):
        return hash(self.attribute)

    def __eq__(self, other):
        return isinstance(other, MyStringable) and self.attribute == other.attribute

    def __lt__(self, other):
        return isinstance(other, MyStringable) and self.attribute < other.attribute

    @staticmethod
    def from_string(str_repr):
        """ Converts a string representation `str_repr` of MyStringable to an instance of MyStringable. """
        return MyStringable(str_repr[len('MyStringable '):])

def test_default_value_type():
    """ Test default value type. """

    for default_value in (True, False, None):
        checker = parsing.DefaultValueType(bool, default_value)
        assert_raises(lambda ch=checker: ch.validate(1), exceptions.TypeException)
        assert_raises(lambda ch=checker: ch.validate(1.1), exceptions.TypeException)
        assert_raises(lambda ch=checker: ch.validate(''), exceptions.TypeException)
        for value in (True, False, None):
            checker.validate(value)
            if value is None:
                assert checker.to_type(value) is default_value
                assert checker.to_json(value) is default_value
            else:
                assert checker.to_type(value) is value
                assert checker.to_json(value) is value
        assert checker.update(None) is default_value

def test_optional_value_type():
    """ Test optional value type. """

    checker = parsing.OptionalValueType(bool)
    assert_raises(lambda ch=checker: ch.validate(1), exceptions.TypeException)
    assert_raises(lambda ch=checker: ch.validate(1.1), exceptions.TypeException)
    assert_raises(lambda ch=checker: ch.validate(''), exceptions.TypeException)
    for value in (True, False, None):
        checker.validate(value)
        assert checker.to_type(value) is value
        assert checker.to_json(value) is value
    assert checker.update(None) is None

def test_sequence_type():
    """ Test sequence type. """

    # With default sequence builder.
    checker = parsing.SequenceType(int)
    checker.validate((1, 2, 3))
    checker.validate([1, 2, 3])
    checker.validate({1, 2, 3})
    checker.validate(SortedSet(int))
    checker.validate(SortedSet(int, (1, 2, 3)))
    assert_raises(lambda: checker.validate((1, 2, 3.0)), exceptions.TypeException)
    assert_raises(lambda: checker.validate((1.0, 2.0, 3.0)), exceptions.TypeException)
    assert isinstance(checker.to_type((1, 2, 3)), list)
    # With SortedSet as sequence builder.
    checker = parsing.SequenceType(float)
    checker.validate((1.0, 2.0, 3.0))
    checker.validate([1.0, 2.0, 3.0])
    checker.validate({1.0, 2.0, 3.0})
    assert_raises(lambda: checker.validate((1, 2, 3.0)), exceptions.TypeException)
    assert_raises(lambda: checker.validate((1.0, 2.0, 3)), exceptions.TypeException)
    checker = parsing.SequenceType(int, sequence_builder=SortedSet.builder(int))
    initial_list = (1, 2, 7, 7, 1)
    checker.validate(initial_list)
    updated_list = checker.update(initial_list)
    assert isinstance(updated_list, SortedSet) and updated_list.element_type is int
    assert updated_list == SortedSet(int, (1, 2, 7))
    assert checker.to_json(updated_list) == [1, 2, 7]
    assert checker.to_type([7, 2, 1, 1, 7, 1, 7]) == updated_list

def test_jsonable_class_type():
    """ Test parser for Jsonable sub-classes. """

    checker = parsing.JsonableClassType(MyJsonable)
    my_jsonable = MyJsonable(field_a=False, field_b='test', field_e={1}, field_f=[6.5])
    my_jsonable_dict = {
        'field_a': False,
        'field_b': 'test',
        'field_e': (1, 2),
        'field_f': (1.0, 2.0),
    }
    checker.validate(my_jsonable)
    assert_raises(lambda: checker.validate(None), exceptions.TypeException)
    assert_raises(lambda: checker.validate(my_jsonable_dict), exceptions.TypeException)

def test_stringable_type():
    """ Test stringable type. """

    checker = parsing.StringableType(str)
    checker.validate('0')
    checker = parsing.StringableType(MyStringable)
    checker.validate(MyStringable('test'))
    assert_raises(lambda: checker.validate('test'), exceptions.TypeException)
    assert_raises(lambda: checker.validate(None), exceptions.TypeException)

def test_dict_type():
    """ Test dict type. """

    checker = parsing.DictType(str, int)
    checker.validate({'test': 1})
    assert_raises(lambda: checker.validate({'test': 1.0}), exceptions.TypeException)
    checker = parsing.DictType(MyStringable, float)
    checker.validate({MyStringable('12'): 2.5})
    assert_raises(lambda: checker.validate({'12': 2.5}), exceptions.TypeException)
    assert_raises(lambda: checker.validate({MyStringable('12'): 2}), exceptions.TypeException)
    checker = parsing.DictType(MyStringable, float, dict_builder=SortedDict.builder(MyStringable, float))
    value = {MyStringable(12): 22.0}
    checker.validate(value)
    updated_value = checker.update(value)
    assert isinstance(updated_value, SortedDict)
    assert updated_value.key_type is MyStringable
    assert updated_value.val_type is float
    json_value = {'MyStringable 12': 22.0}
    assert checker.to_type(json_value) == SortedDict(MyStringable, float, {MyStringable('12'): 22.0})
    assert checker.to_json(SortedDict(MyStringable, float, {MyStringable(12): 22.0})) == json_value

def test_sequence_of_values_type():
    """ Test parser for sequence of allowed values. """

    checker = parsing.EnumerationType({'a', 'b', 'c', 'd'})
    checker.validate('d')
    checker.validate('c')
    checker.validate('b')
    checker.validate('a')
    assert_raises(lambda: checker.validate('e'), exceptions.ValueException)

def test_sequence_of_primitives_type():
    """ Test parser for sequence of primitive types. """

    checker = parsing.SequenceOfPrimitivesType((int, bool))
    checker.validate(False)
    checker.validate(True)
    checker.validate(0)
    checker.validate(1)
    assert_raises(lambda: checker.validate(0.0), exceptions.TypeException)
    assert_raises(lambda: checker.validate(1.0), exceptions.TypeException)
    assert_raises(lambda: checker.validate(''), exceptions.TypeException)
    assert_raises(lambda: checker.validate('a non-empty string'), exceptions.TypeException)

def test_primitive_type():
    """ Test parser for primitive type. """

    checker = parsing.PrimitiveType(bool)
    checker.validate(True)
    checker.validate(False)
    assert_raises(lambda: checker.validate(None), exceptions.TypeException)
    assert_raises(lambda: checker.validate(0), exceptions.TypeException)
    assert_raises(lambda: checker.validate(1), exceptions.TypeException)
    assert_raises(lambda: checker.validate(''), exceptions.TypeException)
    assert_raises(lambda: checker.validate('a non-empty string'), exceptions.TypeException)

def test_model_parsing():
    """ Test parsing for a real model. """

    model = {
        'name': str,
        'language': ('fr', 'en'),
        'myjsonable': parsing.JsonableClassType(MyJsonable),
        'mydict': parsing.DictType(str, float),
        'nothing': (bool, str),
        'default_float': parsing.DefaultValueType(float, 33.44),
        'optional_float': parsing.OptionalValueType(float)
    }
    bad_data_field = {
        '_name_': 'hello',
        'language': 'fr',
        'myjsonable': MyJsonable(field_a=False, field_b='test', field_e={1}, field_f=[6.5]),
        'mydict': {
            'a': 2.5,
            'b': -1.6
        },
        'nothing': 'thanks'
    }
    bad_data_type = {
        'name': 'hello',
        'language': 'fr',
        'myjsonable': MyJsonable(field_a=False, field_b='test', field_e={1}, field_f=[6.5]),
        'mydict': {
            'a': 2.5,
            'b': -1.6
        },
        'nothing': 2.5
    }
    bad_data_value = {
        'name': 'hello',
        'language': '__',
        'myjsonable': MyJsonable(field_a=False, field_b='test', field_e={1}, field_f=[6.5]),
        'mydict': {
            'a': 2.5,
            'b': -1.6
        },
        'nothing': '2.5'
    }
    good_data = {
        'name': 'hello',
        'language': 'fr',
        'myjsonable': MyJsonable(field_a=False, field_b='test', field_e={1}, field_f=[6.5]),
        'mydict': {
            'a': 2.5,
            'b': -1.6
        },
        'nothing': '2.5'
    }
    assert_raises(lambda: parsing.validate_data(bad_data_field, model), (exceptions.TypeException,))
    assert_raises(lambda: parsing.validate_data(bad_data_type, model), (exceptions.TypeException,))
    assert_raises(lambda: parsing.validate_data(bad_data_value, model), (exceptions.ValueException,))

    assert 'default_float' not in good_data
    assert 'optional_float' not in good_data
    parsing.validate_data(good_data, model)
    updated_good_data = parsing.update_data(good_data, model)
    assert 'default_float' in updated_good_data
    assert 'optional_float' in updated_good_data
    assert updated_good_data['default_float'] == 33.44
    assert updated_good_data['optional_float'] is None

def test_converter_type():
    """ Test parser converter type. """

    def converter_to_int(val):
        """ Converts value to integer """
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    checker = parsing.ConverterType(str, converter_function=lambda val: 'String of %s' % val)
    checker.validate('a string')
    checker.validate(10)
    checker.validate(True)
    checker.validate(None)
    checker.validate(-2.5)
    assert checker.update(10) == 'String of 10'
    assert checker.update(False) == 'String of False'
    assert checker.update('string') == 'String of string'
    checker = parsing.ConverterType(int, converter_function=converter_to_int)
    checker.validate(10)
    checker.validate(True)
    checker.validate(None)
    checker.validate(-2.5)
    assert checker.update(10) == 10
    assert checker.update(True) == 1
    assert checker.update(False) == 0
    assert checker.update(-2.5) == -2
    assert checker.update('44') == 44
    assert checker.update('a') == 0

def test_indexed_sequence():
    """ Test parser type for dicts stored as sequences. """
    checker = parsing.IndexedSequenceType(parsing.DictType(str, parsing.JsonableClassType(MyJsonable)), 'field_b')
    sequence = [
        MyJsonable(field_a=True, field_b='x1', field_e=[1, 2, 3], field_f=[1., 2., 3.]),
        MyJsonable(field_a=True, field_b='x3', field_e=[1, 2, 3], field_f=[1., 2., 3.]),
        MyJsonable(field_a=True, field_b='x2', field_e=[1, 2, 3], field_f=[1., 2., 3.]),
        MyJsonable(field_a=True, field_b='x5', field_e=[1, 2, 3], field_f=[1., 2., 3.]),
        MyJsonable(field_a=True, field_b='x4', field_e=[1, 2, 3], field_f=[1., 2., 3.])
    ]
    dct = {element.field_b: element for element in sequence}
    checker.validate(dct)
    checker.update(dct)
    jval = checker.to_json(dct)
    assert isinstance(jval, list), type(jval)
    from_jval = checker.to_type(jval)
    assert isinstance(from_jval, dict), type(from_jval)
    assert len(dct) == 5
    assert len(from_jval) == 5
    for key in ('x1', 'x2', 'x3', 'x4', 'x5'):
        assert key in dct, (key, list(dct.keys()))
        assert key in from_jval, (key, list(from_jval.keys()))
