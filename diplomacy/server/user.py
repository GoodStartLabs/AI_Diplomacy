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
""" User object, defined with a username and a hashed password. """
from diplomacy.utils import strings, parsing
from diplomacy.utils.common import is_valid_password
from diplomacy.utils.jsonable import Jsonable

class User(Jsonable):
    """ User class. """
    __slots__ = ['username', 'password_hash']
    model = {
        strings.USERNAME: str,
        strings.PASSWORD_HASH: str
    }

    def __init__(self, **kwargs):
        self.username = None
        self.password_hash = None
        super(User, self).__init__(**kwargs)

    def is_valid_password(self, password):
        """ Return True if given password matches user hashed password. """
        return is_valid_password(password, self.password_hash)

class DaideUser(User):
    """ DAIDE user class """
    __slots__ = ['username', 'password_hash', 'client_name', 'client_version', 'passcode']
    model = parsing.extend_model(User.model, {
        strings.CLIENT_NAME: str,
        strings.CLIENT_VERSION: str,
        strings.PASSCODE: parsing.OptionalValueType(int)
    })

    def __init__(self, **kwargs):
        self.client_name = ''
        self.client_version = ''
        self.passcode = 0
        super(DaideUser, self).__init__(**kwargs)
