# ==============================================================================
# Copyright (C) 2019 - Philip Paquette
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
""" Settings - Contains a list of utils to help handle DAIDE communication """
from collections import namedtuple
from diplomacy.daide.tokens import is_integer_token, Token

ClientConnection = namedtuple('ClientConnection', ['username', 'daide_user', 'token', 'power_name'])

def get_user_connection(server_users, game, connection_handler):
    """ Get the DAIDE user connection informations

        :param server_users: The instance of `diplomacy.server.users` of the game's server
        :param game: The game the user has joined
        :param connection_handler: The connection_handler of the user
        :return: A tuple of username, daide_user, token, power_name
    """
    token = connection_handler.token
    username = server_users.get_name(token) if server_users.has_token(token) else None
    daide_user = server_users.users.get(username, None)

    # Assumed to be only one power name in the list
    user_powers = [power_name for power_name, power in game.powers.items() if power.is_controlled_by(username)]
    power_name = user_powers[0] if user_powers else None
    return ClientConnection(username, daide_user, token, power_name)

def str_to_bytes(daide_str):
    """ Converts a str into its bytes representation

        :param daide_str: A DAIDE string with tokens separated by spaces
        :return: The bytes representation of the string

        Note: Integers starts with a '#' character
    """
    buffer = []
    str_split = daide_str.split(' ') if daide_str else []
    for word in str_split:
        if word == '':
            buffer.append(bytes(Token(from_str=' ')))
        elif word[0] == '#':
            buffer.append(bytes(Token(from_int=int(word[1:]))))
        else:
            buffer.append(bytes(Token(from_str=word)))
    return b''.join(buffer)

def bytes_to_str(daide_bytes):
    """ Converts a bytes into its str representation

        :param daide_bytes: A DAIDE bytes with tokens separated by spaces
        :return: The bytes representation of the string

        Note: Integers starts with a '#' character
    """
    buffer = []
    length = len(daide_bytes) if daide_bytes else 0
    for i in range(0, length, 2):
        token = Token(from_bytes=(daide_bytes[i], daide_bytes[i + 1]))
        if is_integer_token(token):
            buffer.append('#' + str(token))
        else:
            buffer.append(str(token))
    return ' '.join(buffer)
