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
""" Helper class to manage user accounts and connections  on server side.

    A user is associated to 0 or more connected tokens,
    and each connected token is associated to at most 1 connection handler.

    When a connection handler is closed or invalidated,
    related tokens are kept and may be further associated to new connection handlers.

    Tokens are effectively deleted when they expire after TOKEN_LIFETIME_SECONDS seconds since last token usage.
"""
import logging

from diplomacy.server.user import User
from diplomacy.utils import common, parsing, strings
from diplomacy.utils.common import generate_token
from diplomacy.utils.jsonable import Jsonable

LOGGER = logging.getLogger(__name__)

# Token lifetime in seconds: default 24hours.
TOKEN_LIFETIME_SECONDS = 24 * 60 * 60

class Users(Jsonable):
    """ Users class.

        Properties:

        - **users**: dictionary mapping usernames to User object.s
        - **administrators**: set of administrator usernames.
        - **token_timestamp**: dictionary mapping each token to its creation/last confirmation timestamp.
        - **token_to_username**: dictionary mapping each token to its username.
        - **username_to_tokens**: dictionary mapping each username to a set of its tokens.
        - **token_to_connection_handler**: (memory only) dictionary mapping each token to a connection handler
        - **connection_handler_to_tokens**: (memory only) dictionary mapping a connection handler to a set of its tokens
    """
    __slots__ = ['users', 'administrators', 'token_timestamp', 'token_to_username', 'username_to_tokens',
                 'token_to_connection_handler', 'connection_handler_to_tokens']
    model = {
        strings.USERS: parsing.DefaultValueType(parsing.DictType(str, parsing.JsonableClassType(User)), {}),
        # {username => User}
        strings.ADMINISTRATORS: parsing.DefaultValueType(parsing.SequenceType(str, sequence_builder=set), ()),
        # {usernames}
        strings.TOKEN_TIMESTAMP: parsing.DefaultValueType(parsing.DictType(str, int), {}),
        strings.TOKEN_TO_USERNAME: parsing.DefaultValueType(parsing.DictType(str, str), {}),
        strings.USERNAME_TO_TOKENS: parsing.DefaultValueType(parsing.DictType(str, parsing.SequenceType(str, set)), {}),
    }

    def __init__(self, **kwargs):
        self.users = {}
        self.administrators = set()
        self.token_timestamp = {}
        self.token_to_username = {}
        self.username_to_tokens = {}
        self.token_to_connection_handler = {}
        self.connection_handler_to_tokens = {}
        super(Users, self).__init__(**kwargs)

    def has_username(self, username):
        """ Return True if users have given username. """
        return username in self.users

    def has_user(self, username, password):
        """ Return True if users have given username with given password. """
        return username in self.users and self.users[username].is_valid_password(password)

    def has_admin(self, username):
        """ Return True if given username is an administrator. """
        return username in self.administrators

    def has_token(self, token):
        """ Return True if users have given token. """
        return token in self.token_to_username

    def token_is_alive(self, token):
        """ Return True if given token is known and still alive.
            A token is alive if elapsed time since last token usage does not exceed token lifetime
            (TOKEN_LIFETIME_SECONDS).
        """
        if self.has_token(token):
            current_time = common.timestamp_microseconds()
            elapsed_time_seconds = (current_time - self.token_timestamp[token]) / 1000000
            return elapsed_time_seconds <= TOKEN_LIFETIME_SECONDS
        return False

    def relaunch_token(self, token):
        """ Update timestamp  of given token with current timestamp. """
        if self.has_token(token):
            self.token_timestamp[token] = common.timestamp_microseconds()

    def token_is_admin(self, token):
        """ Return True if given token is associated to an administrator. """
        return self.has_token(token) and self.has_admin(self.get_name(token))

    def count_connections(self):
        """ Return number of registered connection handlers. """
        return len(self.connection_handler_to_tokens)

    def get_tokens(self, username):
        """ Return a sequence of tokens associated to given username. """
        return self.username_to_tokens[username].copy()

    def get_name(self, token):
        """ Return username of given token. """
        return self.token_to_username[token]

    def get_user(self, username):
        """ Returns user linked to username """
        return self.users.get(username, None)

    def get_connection_handler(self, token):
        """ Return connection handler associated to given token, or None if no handler currently associated. """
        return self.token_to_connection_handler.get(token, None)

    def add_admin(self, username):
        """ Set given username as administrator. Related user must exists in this Users object. """
        assert username in self.users
        self.administrators.add(username)

    def remove_admin(self, username):
        """ Remove given username from administrators. """
        if username in self.administrators:
            self.administrators.remove(username)

    def create_token(self):
        """ Return a new token guaranteed to not exist in this Users object. """
        token = generate_token()
        while self.has_token(token):
            token = generate_token()
        return token

    def add_user(self, username, password_hash):
        """ Add a new user with given username and hashed password.
            See diplomacy.utils.common.hash_password() for hashing purposes.
        """
        user = User(username=username, password_hash=password_hash)
        self.users[username] = user
        return user

    def replace_user(self, username, new_user):
        """ Replaces user object with a new user """
        self.users[username] = new_user

    def remove_user(self, username):
        """ Remove user related to given username. """
        user = self.users.pop(username)
        self.remove_admin(username)
        for token in self.username_to_tokens.pop(user.username):
            self.token_timestamp.pop(token)
            self.token_to_username.pop(token)
            connection_handler = self.token_to_connection_handler.pop(token, None)
            if connection_handler:
                self.connection_handler_to_tokens[connection_handler].remove(token)
                if not self.connection_handler_to_tokens[connection_handler]:
                    self.connection_handler_to_tokens.pop(connection_handler)

    def remove_connection(self, connection_handler, remove_tokens=True):
        """ Remove given connection handler.
            Return tokens associated to this connection handler,
            or None if connection handler is unknown.

            :param connection_handler: connection handler to remove.
            :param remove_tokens: if True, tokens related to connection handler are deleted.
            :return: either None or a set of tokens.
        """
        if connection_handler in self.connection_handler_to_tokens:
            tokens = self.connection_handler_to_tokens.pop(connection_handler)
            for token in tokens:
                self.token_to_connection_handler.pop(token)
                if remove_tokens:
                    self.token_timestamp.pop(token)
                    user = self.users[self.token_to_username.pop(token)]
                    self.username_to_tokens[user.username].remove(token)
                    if not self.username_to_tokens[user.username]:
                        self.username_to_tokens.pop(user.username)
            return tokens
        return None

    def connect_user(self, username, connection_handler):
        """ Connect given username to given connection handler with a new generated token,
            and return token generated.

            :param username: username to connect
            :param connection_handler: connection handler to link to user
            :return: a new token generated for connexion
        """
        token = self.create_token()
        user = self.users[username]
        if connection_handler not in self.connection_handler_to_tokens:
            self.connection_handler_to_tokens[connection_handler] = set()
        if user.username not in self.username_to_tokens:
            self.username_to_tokens[user.username] = set()
        self.token_to_username[token] = user.username
        self.token_to_connection_handler[token] = connection_handler
        self.username_to_tokens[user.username].add(token)
        self.connection_handler_to_tokens[connection_handler].add(token)
        self.token_timestamp[token] = common.timestamp_microseconds()
        return token

    def attach_connection_handler(self, token, connection_handler):
        """ Associate given token with given connection handler if token is known.
            If there is a previous connection handler associated to given token, it should be
            the same as given connection handler, otherwise an error is raised
            (meaning previous connection handler was not correctly disconnected from given token.
            It should be a programming error).

            :param token: token
            :param connection_handler: connection handler
        """
        if self.has_token(token):
            previous_connection = self.get_connection_handler(token)
            if previous_connection:
                assert previous_connection == connection_handler, \
                    "A new connection handler cannot be attached to a token always connected to another handler."
            else:
                LOGGER.warning('Attaching a new connection handler to a token.')
                if connection_handler not in self.connection_handler_to_tokens:
                    self.connection_handler_to_tokens[connection_handler] = set()
                self.token_to_connection_handler[token] = connection_handler
                self.connection_handler_to_tokens[connection_handler].add(token)
                self.token_timestamp[token] = common.timestamp_microseconds()

    def disconnect_token(self, token):
        """ Remove given token. """
        self.token_timestamp.pop(token)
        user = self.users[self.token_to_username.pop(token)]
        self.username_to_tokens[user.username].remove(token)
        if not self.username_to_tokens[user.username]:
            self.username_to_tokens.pop(user.username)
        connection_handler = self.token_to_connection_handler.pop(token, None)
        if connection_handler:
            self.connection_handler_to_tokens[connection_handler].remove(token)
            if not self.connection_handler_to_tokens[connection_handler]:
                self.connection_handler_to_tokens.pop(connection_handler)
