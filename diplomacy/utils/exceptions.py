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
""" Exceptions used in diplomacy network code. """

class DiplomacyException(Exception):
    """ Diplomacy network code exception. """

    def __init__(self, message=''):
        self.message = (message or self.__doc__).strip()
        super(DiplomacyException, self).__init__(self.message)

class AlreadyScheduledException(DiplomacyException):
    """ Cannot add a data already scheduled. """

class CommonKeyException(DiplomacyException):
    """Common key error."""

    def __init__(self, key):
        super(CommonKeyException, self).__init__('Forbidden common key in two dicts (%s)' % key)

class KeyException(DiplomacyException):
    """ Key error. """

    def __init__(self, key):
        super(KeyException, self).__init__('Key error: %s' % key)

class LengthException(DiplomacyException):
    """ Length error. """

    def __init__(self, expected_length, given_length):
        super(LengthException, self).__init__('Expected length %d, got %d.' % (expected_length, given_length))

class NaturalIntegerException(DiplomacyException):
    """ Expected a positive integer (int >= 0). """

    def __init__(self, integer_name=''):
        super(NaturalIntegerException, self).__init__(
            ('Integer error: %s.%s' % (integer_name, self.__doc__)) if integer_name else '')

class NaturalIntegerNotNullException(NaturalIntegerException):
    """ Expected a strictly positive integer (int > 0). """

class RandomPowerException(DiplomacyException):
    """ No enough playable powers to select random powers. """

    def __init__(self, nb_powers, nb_available_powers):
        super(RandomPowerException, self).__init__('Cannot randomly select %s power(s) in %s available power(s).'
                                                   % (nb_powers, nb_available_powers))

class TypeException(DiplomacyException):
    """ Type error. """

    def __init__(self, expected_type, given_type):
        super(TypeException, self).__init__('Expected type %s, got type %s' % (expected_type, given_type))

class ValueException(DiplomacyException):
    """ Value error. """

    def __init__(self, expected_values, given_value):
        super(ValueException, self).__init__('Forbidden value %s, expected: %s'
                                             % (given_value, ', '.join(str(v) for v in expected_values)))

class NotificationException(DiplomacyException):
    """ Unknown notification. """

class ResponseException(DiplomacyException):
    """ Unknown response. """

class RequestException(ResponseException):
    """ Unknown request. """

class AdminTokenException(ResponseException):
    """ Invalid token for admin operations. """

class DaidePortException(ResponseException):
    """ Daide server not started for the game """

class GameCanceledException(ResponseException):
    """ Game was cancelled. """

class GameCreationException(ResponseException):
    """ Cannot create more games on that server. """

class GameFinishedException(ResponseException):
    """ This game is finished. """

class GameIdException(ResponseException):
    """ Invalid game ID. """

class GameJoinRoleException(ResponseException):
    """ A token can have only one role inside a game: player, observer or omniscient. """

class GameRoleException(ResponseException):
    """ Game role does not accepts this action. """

class GameMasterTokenException(ResponseException):
    """ Invalid token for master operations. """

class GameNotPlayingException(ResponseException):
    """ Game not playing. """

class GameObserverException(ResponseException):
    """ Disallowed observation for non-master users. """

class GamePhaseException(ResponseException):
    """ Data does not match current game phase. """

    def __init__(self, expected=None, given=None):
        message = self.__doc__.strip()
        # This is to prevent an unexpected Pycharm warning about message type.
        if isinstance(message, bytes):
            message = message.decode()
        if expected is not None:
            message += ' Expected: %s' % expected
        if given is not None:
            message += ' Given: %s' % given
        super(GamePhaseException, self).__init__(message)

class GamePlayerException(ResponseException):
    """ Invalid player. """

class GameRegistrationPasswordException(ResponseException):
    """ Invalid game registration password. """

class GameSolitaireException(ResponseException):
    """ A solitaire game does not accepts players. """

class GameTokenException(ResponseException):
    """ Invalid token for this game. """

class MapIdException(ResponseException):
    """ Invalid map ID. """

class MapPowerException(ResponseException):
    """ Invalid map power. """

    def __init__(self, power_name):
        super(MapPowerException, self).__init__('Invalid map power %s' % power_name)

class FolderException(ResponseException):
    """ Given folder not available in server. """
    def __init__(self, folder_path):
        super(FolderException, self).__init__('Given folder not available in server: %s' % folder_path)

class ServerRegistrationException(ResponseException):
    """ Registration currently not allowed on this server. """

class TokenException(ResponseException):
    """ Invalid token. """

class UserException(ResponseException):
    """ Invalid user. """

class PasswordException(ResponseException):
    """ Password must not be empty. """

class ServerDirException(ResponseException):
    """ Error with working folder. """

    def __init__(self, server_dir):
        super(ServerDirException, self).__init__("No server directory available at path %s" % server_dir)
