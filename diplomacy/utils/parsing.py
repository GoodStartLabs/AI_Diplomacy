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
""" Provide classes and methods to parse python objects.

    Useful for type checking and conversions from/to JSON dictionaries.

    This module use 2 definitions to distinguish values from/to JSON: item values and attribute values.

    Item value is a value retrieved from a JSON dictionary. It's generally a basic Python type
    (e.g. bool, int, str, float).

    Attribute value is a value used in Python code and expected by type checking. It may be
    a basic Python type, or a class instance. Note that not all classes are allowed (see
    other type checkers below).

"""
import inspect
import logging
from abc import ABCMeta, abstractmethod
from copy import copy

from diplomacy.utils import exceptions
from diplomacy.utils.common import assert_no_common_keys, is_dictionary, is_sequence

LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------
# ------------          Functions       ---------------
# -----------------------------------------------------

def update_model(model, additional_keys, allow_duplicate_keys=True):
    """ Return a copy of model updated with additional keys.

        :param model: (Dictionary). Model to extend
        :param additional_keys: (Dictionary). Definition of the additional keys to use to update the model.
        :param allow_duplicate_keys: Boolean. If True, the model key will be updated if present in additional keys.
                                     Otherwise, an error is thrown if additional_key contains a model key.
        :return: The updated model with the additional keys.
    """
    assert isinstance(model, dict)
    assert isinstance(additional_keys, dict)
    if not allow_duplicate_keys:
        assert_no_common_keys(model, additional_keys)
    model_copy = model.copy()
    model_copy.update(additional_keys)
    return model_copy

def extend_model(model, additional_keys):
    """ Return a copy of model updated with additional model keys. Model and additional keys must no share any key.

        :param model: (Dictionary). Model to update
        :param additional_keys: (Dictionary). Definition of the additional keys to add to model.
        :return: The updated model with the additional keys.
    """
    return update_model(model, additional_keys, allow_duplicate_keys=False)

def get_type(desired_type):
    """ Return a ParserType sub-class that matches given type.

        :param desired_type: basic type or ParserType sub-class.
        :return: ParserType sub-class instance.
    """
    # Already a ParserType, we return the object directly.
    if isinstance(desired_type, ParserType):
        return desired_type

    # Sequence of primitive.
    # Detecting if we have a sequence of primitive classes or instances (values).
    if isinstance(desired_type, (list, tuple, set)) and desired_type:
        if inspect.isclass(next(iter(desired_type))):
            return SequenceOfPrimitivesType(desired_type)
        return EnumerationType(desired_type)

    # By default, we return a Type(expected_type).
    # If expected_type is not a basic type, an exception will be raised
    # (see class Type above).
    return PrimitiveType(desired_type)

def to_type(json_value, parser_type):
    """ Convert a JSON value (python built-in type) to the type described by parser_type.

        :param json_value: JSON value to convert.
        :param parser_type: either an instance of a ParserType, or a type convertible
            to a ParserType (see function get_type() above).
        :return: JSON value converted to expected type.
    """
    return get_type(parser_type).to_type(json_value)

def to_json(raw_value, parser_type):
    """ Convert a value from the type described by parser_type to a JSON value.

        :param raw_value: The raw value to convert to JSON.
        :param parser_type: Either an instance of a ParserType, or a type convertible to a ParserType.
        :return: The value converted to an equivalent JSON value.
    """
    return get_type(parser_type).to_json(raw_value)

def validate_data(data, model):
    """ Validates that the data complies with the model

        :param data: (Dictionary). A dict of values to validate against the model.
        :param model: (Dictionary). The model to use for validation.
    """
    assert isinstance(data, dict)
    assert isinstance(model, dict)

    # Make sure all fields in data are of the correct type.
    # Also make sure all expected fields not present in data have default values (e.g. None).
    # NB: We don't care about extra keys in provided data. We only focus on expected keys.
    for model_key, model_type in model.items():
        try:
            get_type(model_type).validate(data.get(model_key, None))
        except exceptions.TypeException as exception:
            LOGGER.error('Error occurred while checking key %s', model_key)
            raise exception

def update_data(data, model):
    """ Modifies the data object to add default values if needed

        :param data: (Dictionary). A dict of values to update.
        :param model: (Dictionary). The model to use.
    """
    # Updating the data types
    for model_key, model_type in model.items():
        data_value = data.get(model_key, None)
        # update() will return either same value or updated value.
        data[model_key] = get_type(model_type).update(data_value)
    return data

# -----------------------------------------------------
# ------------          Classes         ---------------
# -----------------------------------------------------

class ParserType(metaclass=ABCMeta):
    """ Abstract base class to check a specific type. """
    __slots__ = []
    # We include dict into primitive types to allow parser to accept raw untyped dict
    # (e.g. engine game state).
    primitives = (bytes, int, float, bool, str, dict)

    @abstractmethod
    def validate(self, element):
        """ Makes sure the element is a valid element for this parser type

            :param element: The element to validate.
            :return: None, but raises Error if needed.
        """
        raise NotImplementedError()

    def update(self, element):
        """ Returns the correct value to use in the data object.

            :param element: The element the model wants to store in the data object of this parser type.
            :return: The updated element to store in the data object.
                     The updated element might be a different value (e.g. if a default value is present)
        """
        # pylint: disable=no-self-use
        return element

    def to_type(self, json_value):
        """ Converts a json_value to this parser type.

            :param json_value: The JSON value to convert.
            :return: The converted JSON value.
        """
        # pylint: disable=no-self-use
        return json_value

    def to_json(self, raw_value):
        """ Converts a raw value (of this type) to JSON.

            :param raw_value: The raw value (of this type) to convert.
            :return: The resulting JSON value.
        """
        # pylint: disable=no-self-use
        return raw_value

class ConverterType(ParserType):
    """ Type checker that allows to use another parser type with a converter function.
        Converter function will be used to convert any raw value to a value expected
        by given parser type before validations and updates.
    """
    def __init__(self, element_type, converter_function, json_converter_function=None):
        """ Initialize a converter type.

            :param element_type: expected type
            :param converter_function: function to be used to check and convert values to expected type.
                converter_function(value) -> value_compatible_with_expected_type
            :param json_converter_function: function to be used to convert a JSON value
                to an expected JSON value for element_type. If not provided, converter_function will be used.
                json_converter_function(json_value) -> new JSON value valid for element_type.to_type(new_json_value)
        """
        element_type = get_type(element_type)
        assert not isinstance(element_type, ConverterType)
        assert callable(converter_function)
        self.element_type = element_type
        self.converter_function = converter_function
        self.json_converter_function = json_converter_function or converter_function

    def validate(self, element):
        self.element_type.validate(self.converter_function(element))

    def update(self, element):
        return self.element_type.update(self.converter_function(element))

    def to_type(self, json_value):
        return self.element_type.to_type(self.json_converter_function(json_value))

    def to_json(self, raw_value):
        return self.element_type.to_json(raw_value)

class DefaultValueType(ParserType):
    """ Type checker that allows a default value. """
    __slots__ = ('element_type', 'default_json_value')

    def __init__(self, element_type, default_json_value):
        """ Initialize a default type checker with expected element type and a default value (if None is present).

            :param element_type: The expected type for elements (except if None is provided).
            :param default_json_value: The default value to set if element=None. Must be a JSON value
                convertible to element_type, so that new default value is generated from this JSON value
                each time it's needed.
        """
        element_type = get_type(element_type)
        assert not isinstance(element_type, (DefaultValueType, OptionalValueType))
        self.element_type = element_type
        self.default_json_value = default_json_value
        # If default JSON value is provided, make sure it's a valid value.
        if default_json_value is not None:
            self.validate(self.to_type(default_json_value))

    def __str__(self):
        """ String representation """
        return '%s (default %s)' % (self.element_type, self.default_json_value)

    def validate(self, element):
        if element is not None:
            self.element_type.validate(element)

    def update(self, element):
        if element is not None:
            return self.element_type.update(element)
        return None if self.default_json_value is None else self.element_type.to_type(self.default_json_value)

    def to_type(self, json_value):
        json_value = self.default_json_value if json_value is None else json_value
        return None if json_value is None else self.element_type.to_type(json_value)

    def to_json(self, raw_value):
        return copy(self.default_json_value) if raw_value is None else self.element_type.to_json(raw_value)

class OptionalValueType(DefaultValueType):
    """ Type checker that allows None as default value. """
    __slots__ = []

    def __init__(self, element_type):
        """ Initialized a optional type checker with expected element type.

            :param element_type: The expected type for elements.
        """
        super(OptionalValueType, self).__init__(element_type, None)

class SequenceType(ParserType):
    """ Type checker for sequence-like objects. """
    __slots__ = ['element_type', 'sequence_builder']

    def __init__(self, element_type, sequence_builder=None):
        """ Initialize a sequence type checker with value type and optional sequence builder.

            :param element_type: Expected type for sequence elements.
            :param sequence_builder: (Optional). A callable used to build the sequence type.
                                     Expected args: Iterable
        """
        self.element_type = get_type(element_type)
        self.sequence_builder = sequence_builder if sequence_builder is not None else lambda seq: seq

    def __str__(self):
        """ String representation """
        return '[%s]' % self.element_type

    def validate(self, element):
        if not is_sequence(element):
            raise exceptions.TypeException('sequence', type(element))
        for seq_element in element:
            self.element_type.validate(seq_element)

    def update(self, element):
        # Converting each element in the list, then using the seq builder if available
        sequence = [self.element_type.update(seq_element) for seq_element in element]
        return self.sequence_builder(sequence)

    def to_type(self, json_value):
        sequence = [self.element_type.to_type(seq_element) for seq_element in json_value]
        return self.sequence_builder(sequence)

    def to_json(self, raw_value):
        return [self.element_type.to_json(seq_element) for seq_element in raw_value]

class JsonableClassType(ParserType):
    """ Type checker for Jsonable classes. """
    __slots__ = ['element_type']

    def __init__(self, jsonable_element_type):
        """ Initialize a sub-class of Jsonable.

            :param jsonable_element_type: Expected type (should be a subclass of Jsonable).
        """
        # We import Jsonable here to prevent recursive import with module jsonable.
        from diplomacy.utils.jsonable import Jsonable
        assert issubclass(jsonable_element_type, Jsonable)
        self.element_type = jsonable_element_type

    def __str__(self):
        """ String representation """
        return self.element_type.__name__

    def validate(self, element):
        if not isinstance(element, self.element_type):
            raise exceptions.TypeException(self.element_type, type(element))

    def to_type(self, json_value):
        return self.element_type.from_dict(json_value)

    def to_json(self, raw_value):
        return raw_value.to_dict()

class StringableType(ParserType):
    """ Type checker for a class that can be converted to a string with str(obj)
        and converted from a string with cls.from_string(str_val) or cls(str_val).

        In practice, this parser will just save object as string with str(obj),
        and load object from string using cls(str_val) or cls.from_string(str_val).
        So, object may have any type as long as:
        str(obj) == str( object loaded from str(obj) )

        Expected type: a class with compatible str(cls(str_repr)) or str(cls.from_string(str_repr)).
    """
    __slots__ = ['element_type', 'use_from_string']

    def __init__(self, element_type):
        """ Initialize a parser type with a type convertible from/to string.

            :param element_type:  Expected type. Needs to be convertible to/from String.
        """
        if hasattr(element_type, 'from_string'):
            assert callable(element_type.from_string)
            self.use_from_string = True
        else:
            self.use_from_string = False
        self.element_type = element_type

    def __str__(self):
        """ String representation """
        return self.element_type.__name__

    def validate(self, element):
        if not isinstance(element, self.element_type):
            try:
                # Check if given element can be handled by element type.
                element_to_str = self.to_json(element)
                element_from_str = self.to_type(element_to_str)
                element_from_str_to_str = self.to_json(element_from_str)
                assert element_to_str == element_from_str_to_str
            except Exception:
                # Given element can't be handled, raise a type exception.
                raise exceptions.TypeException(self.element_type, type(element))

    def to_type(self, json_value):
        if self.use_from_string:
            return self.element_type.from_string(json_value)
        return self.element_type(json_value)

    def to_json(self, raw_value):
        return str(raw_value)

class DictType(ParserType):
    """ Type checking for dictionary-like objects. """
    __slots__ = ['key_type', 'val_type', 'dict_builder']

    def __init__(self, key_type, val_type, dict_builder=None):
        """ Initialize a dict parser type with expected key type, val type, and optional dict builder.

            :param key_type: The expected key type. Must be string or a stringable class.
            :param val_type: The expected value type.
            :param dict_builder: Callable to build attribute values.
        """
        # key type muse be convertible from/to string.
        self.key_type = key_type if isinstance(key_type, StringableType) else StringableType(key_type)
        self.val_type = get_type(val_type)
        self.dict_builder = dict_builder if dict_builder is not None else lambda dictionary: dictionary

    def __str__(self):
        """ String representation """
        return '{%s => %s}' % (self.key_type, self.val_type)

    def validate(self, element):
        if not is_dictionary(element):
            raise exceptions.TypeException('dictionary', type(element))
        for key, value in element.items():
            self.key_type.validate(key)
            self.val_type.validate(value)

    def update(self, element):
        return_dict = {self.key_type.update(key): self.val_type.update(value) for key, value in element.items()}
        return self.dict_builder(return_dict)

    def to_type(self, json_value):
        json_dict = {self.key_type.to_type(key): self.val_type.to_type(value) for key, value in json_value.items()}
        return self.dict_builder(json_dict)

    def to_json(self, raw_value):
        return {self.key_type.to_json(key): self.val_type.to_json(value) for key, value in raw_value.items()}

class IndexedSequenceType(ParserType):
    """ Parser for objects stored as dictionaries in memory and saved as lists in JSON. """
    __slots__ = ['dict_type', 'sequence_type', 'key_name']

    def __init__(self, dict_type, key_name):
        """ Initializer.

            :param dict_type: dictionary parser type to be used to manage object in memory.
            :param key_name: name of attribute to take in sequence elements to convert sequence to a dictionary.
                dct = {getattr(element, key_name): element for element in sequence}
                sequence = list(dct.values())
        """
        assert isinstance(dict_type, DictType)
        self.dict_type = dict_type
        self.sequence_type = SequenceType(self.dict_type.val_type)
        self.key_name = str(key_name)

    def __str__(self):
        return '{%s.%s}' % (self.dict_type.val_type, self.key_name)

    def validate(self, element):
        self.dict_type.validate(element)

    def update(self, element):
        return self.dict_type.update(element)

    def to_json(self, raw_value):
        """ Dict is saved as a sequence. """
        return self.sequence_type.to_json(raw_value.values())

    def to_type(self, json_value):
        """ JSON is parsed as a sequence and converted to a dict. """
        loaded_sequence = self.sequence_type.to_type(json_value)
        return self.dict_type.update({getattr(element, self.key_name): element for element in loaded_sequence})

class EnumerationType(ParserType):
    """ Type checker for a set of allowed basic values. """
    __slots__ = ['enum_values']

    def __init__(self, enum_values):
        """ Initialize sequence of values type with a sequence of allowed (primitive) values.

            :param enum_values: Sequence of allowed values.
        """
        enum_values = set(enum_values)
        assert enum_values and all(isinstance(value, self.primitives) for value in enum_values)
        self.enum_values = enum_values

    def __str__(self):
        """ String representation """
        return 'in (%s)' % (', '.join(str(e) for e in sorted(self.enum_values)))

    def validate(self, element):
        if not any(type(element) is type(value) and element == value for value in self.enum_values):
            raise exceptions.ValueException(self.enum_values, element)

    def to_type(self, json_value):
        """ For enumerations, we will validate JSON value before parsing it. """
        self.validate(json_value)
        return json_value

class SequenceOfPrimitivesType(ParserType):
    """ Type checker for a set of allowed basic types. """
    __slots__ = ['seq_of_primitives']

    def __init__(self, seq_of_primitives):
        """ Initialize sequence of primitives type with a sequence of allowed primitives.

            :param seq_of_primitives: Sequence of primitives.
        """
        assert seq_of_primitives and all(primitive in self.primitives for primitive in seq_of_primitives)
        self.seq_of_primitives = seq_of_primitives if isinstance(seq_of_primitives, tuple) else tuple(seq_of_primitives)

    def __str__(self):
        """ String representation """
        return 'type in: %s' % (', '.join(t.__name__ for t in self.seq_of_primitives))

    def validate(self, element):
        if not isinstance(element, self.seq_of_primitives):
            raise exceptions.TypeException(self.seq_of_primitives, type(element))

class PrimitiveType(ParserType):
    """ Type checker for a primitive type. """
    __slots__ = ['element_type']

    def __init__(self, element_type):
        """ Initialize a primitive type.

            :param element_type: Primitive type.
        """
        assert element_type in self.primitives, 'Expected a primitive type, got %s.' % element_type
        self.element_type = element_type

    def __str__(self):
        """ String representation """
        return self.element_type.__name__

    def validate(self, element):
        if not isinstance(element, self.element_type):
            raise exceptions.TypeException(self.element_type, type(element))
