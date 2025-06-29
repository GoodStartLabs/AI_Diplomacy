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
""" Abstract Jsonable class with automatic attributes checking and conversion to/from JSON dict.
    To write a Jsonable sub-class:

    - Define a model with expected attribute names and types. Use module `parsing` to describe expected types.
    - Override initializer ``__init__(**kwargs)``:

        - **first**: initialize each attribute defined in model with value None.
        - **then** : call parent __init__() method. Attributes will be checked and filled by
          Jsonable's __init__() method.
        - If needed, add further initialization code after call to parent __init__() method. At this point,
          attributes were correctly set based on defined model, and you can now work with them.

    Example:

    .. code-block:: python

        class MyClass(Jsonable):
            model = {
                'my_attribute': parsing.Sequence(int),
            }
            def __init__(**kwargs):
                self.my_attribute = None
                super(MyClass, self).__init__(**kwargs)
                # my_attribute is now initialized based on model.
                # You can then do any further initialization if needed.

"""
import logging
import ujson as json

from diplomacy.utils import exceptions, parsing

LOGGER = logging.getLogger(__name__)

class Jsonable:
    """ Abstract class to ease conversion from/to JSON dict. """
    __slots__ = []
    __cached__models__ = {}
    model = {}

    def __init__(self, **kwargs):
        """ Validates given arguments, update them if necessary (e.g. to add default values),
            and fill instance attributes with updated argument.
            If a derived class adds new attributes, it must override __init__() method and
            initialize new attributes (e.g. `self.attribute = None`)
            **BEFORE** calling parent __init__() method.

            :param kwargs: arguments to build class. Must match keys and values types defined in model.
        """
        model = self.get_model()

        # Adding default value
        updated_kwargs = {model_key: None for model_key in model}
        updated_kwargs.update(kwargs)

        # Validating and updating
        try:
            parsing.validate_data(updated_kwargs, model)
        except exceptions.TypeException as exception:
            LOGGER.error('Error occurred while building class %s', self.__class__)
            raise exception
        updated_kwargs = parsing.update_data(updated_kwargs, model)

        # Building.
        for model_key in model:
            setattr(self, model_key, updated_kwargs[model_key])

    def json(self):
        """ Convert this object to a JSON string ready to be sent/saved.

            :return: string
        """
        return json.dumps(self.to_dict())

    def to_dict(self):
        """ Convert this object to a python dictionary ready for any JSON work.

            :return: dict
        """
        model = self.get_model()
        return {key: parsing.to_json(getattr(self, key), key_type) for key, key_type in model.items()}

    @classmethod
    def update_json_dict(cls, json_dict):
        """ Update a JSON dictionary before being parsed with class model.
            JSON dictionary is passed by class method from_dict() (see below), and is guaranteed to contain
            at least all expected model keys. Some keys may be associated to None if initial JSON dictionary
            did not provide values for them.

            :param json_dict: a JSON dictionary to be parsed.
            :type json_dict: dict
        """

    @classmethod
    def from_dict(cls, json_dict):
        """ Convert a JSON dictionary to an instance of this class.

            :param json_dict: a JSON dictionary to parse. Dictionary with basic types (int, bool, dict, str, None, etc.)
            :return: an instance from this class or from a derived one from which it's called.
            :rtype: cls
        """
        model = cls.get_model()

        # json_dict must be a a dictionary
        if not isinstance(json_dict, dict):
            raise exceptions.TypeException(dict, type(json_dict))

        # By default, we set None for all expected keys
        default_json_dict = {key: None for key in model}
        default_json_dict.update(json_dict)
        cls.update_json_dict(json_dict)

        # Building this object
        # NB: We don't care about extra keys in provided dict, we just focus on expected keys, nothing more.
        kwargs = {key: parsing.to_type(default_json_dict[key], key_type) for key, key_type in model.items()}
        return cls(**kwargs)

    @classmethod
    def build_model(cls):
        """ Return model associated to current class. You can either define model class field
            or override this function.
        """
        return cls.model

    @classmethod
    def get_model(cls):
        """ Return model associated to current class, and cache it for future uses, to avoid
            multiple rendering of model for each class derived from Jsonable. Private method.

            :return: dict: model associated to current class.
        """
        if cls not in cls.__cached__models__:
            cls.__cached__models__[cls] = cls.build_model()
        return cls.__cached__models__[cls]
