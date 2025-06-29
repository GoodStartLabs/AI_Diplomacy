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
""" Abstract Jsonable class to create data intended to be exchanged on network.

    Used for requests, responses and notifications.
    To write a sub-class, you must first write a base class for data category (e.g. notifications):

    - Define header model for network data.
    - Define ID field for data category (e.g. "notification_id"). This will be used to create unique
      identifier for every data exchanged on network.
    - Then every sub-class from base class must define parameters (params) model. Params and header
      must not share any field.
"""
import uuid

from diplomacy.utils import strings, exceptions
from diplomacy.utils.common import assert_no_common_keys, camel_case_to_snake_case
from diplomacy.utils.jsonable import Jsonable

class NetworkData(Jsonable):
    """ Abstract class for network-exchanged data. """
    __slots__ = ['name']
    # NB: header must have a `name` field and a field named `id_field`.
    header = {}
    params = {}
    id_field = None

    def __init__(self, **kwargs):
        self.name = None  # type: str

        # Setting default values
        kwargs[strings.NAME] = kwargs.get(strings.NAME, None) or self.get_class_name()
        kwargs[self.id_field] = kwargs.get(self.id_field, None) or str(uuid.uuid4())
        if kwargs[strings.NAME] != self.get_class_name():
            raise exceptions.DiplomacyException('Expected request name %s, got %s' %
                                                (self.get_class_name(), kwargs[strings.NAME]))

        # Building
        super(NetworkData, self).__init__(**kwargs)

    @classmethod
    def get_class_name(cls):
        """ Returns the class name in snake_case. """
        return camel_case_to_snake_case(cls.__name__)

    @classmethod
    def validate_params(cls):
        """ Called when getting model to validate parameters. Called once per class. """

    @classmethod
    def build_model(cls):
        """ Return model associated to current class. You can either define model class field
            or override this function.
        """
        # Validating model parameters (header and params must have different keys)
        assert_no_common_keys(cls.header, cls.params)
        cls.validate_params()

        # Building model.
        model = cls.header.copy()
        model.update(cls.params.copy())
        model[strings.NAME] = (cls.get_class_name(),)
        return model
