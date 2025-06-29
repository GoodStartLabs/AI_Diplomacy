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
""" Test changes in a Jsonable schema. """
#pylint: disable=invalid-name
from diplomacy.utils import parsing
from diplomacy.utils.jsonable import Jsonable

def converter_to_int(val):
    """ A converter from given value to an integer. Used in Version1. """
    try:
        return int(val)
    except ValueError:
        return 0

class Version1(Jsonable):
    """ A Jsonable with fields a, b, c, d.
        NB: To parse a dict from Version22 to Version1, modified fields a and c must be convertible in Version1.
        using ConverterType in Version1.
    """
    model = {
        'a': parsing.ConverterType(int, converter_to_int),
        'b': parsing.OptionalValueType(str),
        'c': parsing.ConverterType(float, converter_function=float),
        'd': parsing.DefaultValueType(bool, True),
    }

    def __init__(self, **kwargs):
        self.a = None
        self.b = None
        self.c = None
        self.d = None
        super(Version1, self).__init__(**kwargs)

class Version20(Jsonable):
    """ Version1 with removed fields b and d.
        NB: To parse a dict from Version20 to Version1, removed fields b and d must be optional in Version1.
    """
    model = {
        'a': int,
        'c': float,
    }

    def __init__(self, **kwargs):
        self.a = None
        self.c = None
        super(Version20, self).__init__(**kwargs)

class Version21(Jsonable):
    """ Version1 with added fields e and f.
        NB: To parse a dict from Version1 to Version21, added fields e and f must be optional in Version21.
    """
    model = {
        'a': int,
        'b': str,
        'c': float,
        'd': bool,
        'e': parsing.DefaultValueType(parsing.EnumerationType([100, 200, 300, 400]), 100),
        'f': parsing.DefaultValueType(dict, {'x': 1, 'y': 2})
    }

    def __init__(self, **kwargs):
        self.a = None
        self.b = None
        self.c = None
        self.d = None
        self.e = None
        self.f = {}
        super(Version21, self).__init__(**kwargs)

class Version22(Jsonable):
    """ Version1 with modified types for a and c.
        NB: To parse a dict from Version1 to Version22, modified fields a and c must be convertible
        using ConverterType in Version22.
    """
    model = {
        'a': parsing.ConverterType(str, converter_function=str),
        'b': str,
        'c': parsing.ConverterType(bool, converter_function=bool),
        'd': bool,
    }

    def __init__(self, **kwargs):
        self.a = None
        self.b = None
        self.c = None
        self.d = None
        super(Version22, self).__init__(**kwargs)

class Version3(Jsonable):
    """ Version 1 with a modified, b removed, e added.
        To parse a dict between Version3 and Version1:

            - a must be convertible in both versions.
            - b must be optional in Version1.
            - e must be optional in Version3.
    """
    model = {
        'a': parsing.ConverterType(str, converter_function=str),
        'c': float,
        'd': bool,
        'e': parsing.OptionalValueType(parsing.SequenceType(int))
    }

    def __init__(self, **kwargs):
        self.a = None
        self.c = None
        self.d = None
        self.e = None
        super(Version3, self).__init__(**kwargs)

def test_jsonable_changes_v1_v20():
    """ Test changes from Version1 to Version20. """
    v20 = Version20(a=1, c=1.5)
    v1 = Version1(a=1, b='b', c=1.5, d=False)
    json_v1 = v1.to_dict()
    v20_from_v1 = Version20.from_dict(json_v1)
    json_v20_from_v1 = v20_from_v1.to_dict()
    v1_from_v20_from_v1 = Version1.from_dict(json_v20_from_v1)
    assert v1_from_v20_from_v1.b is None
    assert v1_from_v20_from_v1.d is True
    json_v20 = v20.to_dict()
    v1_from_v20 = Version1.from_dict(json_v20)
    assert v1_from_v20.b is None
    assert v1_from_v20.d is True

def test_jsonable_changes_v1_v21():
    """ Test changes from Version1 to Version21. """
    v21 = Version21(a=1, b='b21', c=1.5, d=True, e=300, f=dict(x=1, y=2))
    v1 = Version1(a=1, b='b', c=1.5, d=False)
    json_v1 = v1.to_dict()
    v21_from_v1 = Version21.from_dict(json_v1)
    assert v21_from_v1.e == 100
    assert v21_from_v1.f['x'] == 1
    assert v21_from_v1.f['y'] == 2
    json_v21_from_v1 = v21_from_v1.to_dict()
    v1_from_v21_from_v1 = Version1.from_dict(json_v21_from_v1)
    assert v1_from_v21_from_v1.b == 'b'
    assert v1_from_v21_from_v1.d is False
    json_v21 = v21.to_dict()
    v1_from_v21 = Version1.from_dict(json_v21)
    assert v1_from_v21.b == 'b21'
    assert v1_from_v21.d is True

def test_jsonable_changes_v1_v22():
    """ Test changes from Version1 to Version22. """
    v22 = Version22(a='a', b='b', c=False, d=False)
    v1 = Version1(a=1, b='b', c=1.5, d=False)
    json_v1 = v1.to_dict()
    v22_from_v1 = Version22.from_dict(json_v1)
    assert v22_from_v1.a == '1'
    assert v22_from_v1.c is True
    json_v22_from_v1 = v22_from_v1.to_dict()
    v1_from_v22_from_v1 = Version1.from_dict(json_v22_from_v1)
    assert v1_from_v22_from_v1.a == 1
    assert v1_from_v22_from_v1.c == 1.0
    json_v22 = v22.to_dict()
    v1_from_v22 = Version1.from_dict(json_v22)
    assert v1_from_v22.a == 0
    assert v1_from_v22.c == 0.0

def test_jsonable_changes_v1_v3():
    """ Test changes from Version1 to Version3. """
    v3 = Version3(a='a', c=1.5, d=False, e=(1, 2, 3))
    v1 = Version1(a=1, b='b', c=1.5, d=False)
    json_v1 = v1.to_dict()
    v3_from_v1 = Version3.from_dict(json_v1)
    assert v3_from_v1.a == '1'
    assert v3_from_v1.e is None
    json_v3_from_v1 = v3_from_v1.to_dict()
    v1_from_v3_from_v1 = Version1.from_dict(json_v3_from_v1)
    assert v1_from_v3_from_v1.a == 1
    assert v1_from_v3_from_v1.b is None
    json_v3 = v3.to_dict()
    v1_from_v3 = Version1.from_dict(json_v3)
    assert v1_from_v3.a == 0
    assert v1_from_v3.b is None
