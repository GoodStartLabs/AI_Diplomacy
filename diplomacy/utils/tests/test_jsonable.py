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
""" Test Jsonable. """
import ujson as json

from diplomacy.utils import parsing
from diplomacy.utils.jsonable import Jsonable
from diplomacy.utils.sorted_dict import SortedDict
from diplomacy.utils.sorted_set import SortedSet

class MyJsonable(Jsonable):
    """ Example of class derived from Jsonable. """
    __slots__ = ('field_a', 'field_b', 'field_c', 'field_d', 'field_e', 'field_f', 'field_g')

    model = {
        'field_a': bool,
        'field_b': str,
        'field_c': parsing.OptionalValueType(float),
        'field_d': parsing.DefaultValueType(str, 'super'),
        'field_e': parsing.SequenceType(int),
        'field_f': parsing.SequenceType(float, sequence_builder=SortedSet.builder(float)),
        'field_g': parsing.DefaultValueType(parsing.DictType(str, int, SortedDict.builder(str, int)), {'x': -1})
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.field_a = None
        self.field_b = None
        self.field_c = None
        self.field_d = None
        self.field_e = None
        self.field_f = None
        self.field_g = {}
        super(MyJsonable, self).__init__(**kwargs)

def test_jsonable_parsing():
    """ Test parsing for Jsonable. """

    attributes = ('field_a', 'field_b', 'field_c', 'field_d', 'field_e', 'field_f', 'field_g')

    # Building and validating
    my_jsonable = MyJsonable(field_a=False, field_b='test', field_e={1}, field_f=[6.5])
    for attribute_name in attributes:
        assert hasattr(my_jsonable, attribute_name)
    assert isinstance(my_jsonable.field_a, bool)
    assert isinstance(my_jsonable.field_b, str)
    assert my_jsonable.field_c is None
    assert isinstance(my_jsonable.field_d, str), my_jsonable.field_d
    assert isinstance(my_jsonable.field_e, list)
    assert isinstance(my_jsonable.field_f, SortedSet)
    assert isinstance(my_jsonable.field_g, SortedDict)
    assert my_jsonable.field_d == 'super'
    assert my_jsonable.field_e == [1]
    assert my_jsonable.field_f == SortedSet(float, (6.5,))
    assert len(my_jsonable.field_g) == 1 and my_jsonable.field_g['x'] == -1

    # Building from its json representation and validating
    from_json = MyJsonable.from_dict(json.loads(json.dumps(my_jsonable.to_dict())))
    for attribute_name in attributes:
        assert hasattr(from_json, attribute_name), attribute_name
    assert from_json.field_a == my_jsonable.field_a
    assert from_json.field_b == my_jsonable.field_b
    assert from_json.field_c == my_jsonable.field_c
    assert from_json.field_d == my_jsonable.field_d
    assert from_json.field_e == my_jsonable.field_e
    assert from_json.field_f == my_jsonable.field_f
    assert from_json.field_g == my_jsonable.field_g
