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
""" Set of games instances (NetworkGame objects) for a same game ID for 1 channel.
    Contains at most 1 game instance per map power + 1 "special" game which is either
    an observer game or an omniscient game. A game instance set cannot contain both
    an observer game and an omniscient game because 1 channel (ie. 1 user connected
    with 1 token) can be either an observer or an omniscient,
    but not both at same time.
"""
import weakref

from diplomacy.engine.game import Game
from diplomacy.utils import exceptions

class GameInstancesSet():
    """ Game Instances Set class. """
    __slots__ = ['game_id', 'games', 'current_observer_type']

    def __init__(self, game_id):
        """ Initialize a game instances set.

            :param game_id: game ID of game instances to store.
            :type game_id: str
        """
        self.game_id = game_id
        self.games = weakref.WeakValueDictionary()  # {power name => NetworkGame}
        self.current_observer_type = None

    def get_games(self):
        """ Return a sequence of stored game instances. """
        return self.games.values()

    def get(self, power_name):
        """ Return game instance associated to given power name. """
        return self.games.get(power_name, None)

    def get_special(self):
        """ Return stored special game, or None if no special game found. """
        return self.games.get(self.current_observer_type, None) if self.current_observer_type else None

    def remove(self, role):
        """ Remove game instance associated to given game role. """
        return self.games.pop(role, None)

    def remove_special(self):
        """ Remove special gme.  """
        self.games.pop(self.current_observer_type, None)

    def add(self, game):
        """ Add given game.

            :param game: a NetworkGame object.
            :type game: diplomacy.client.network_game.NetworkGame
        """
        assert self.game_id == game.game_id
        if Game.is_player_game(game):
            if game.role in self.games:
                raise exceptions.DiplomacyException('Power name %s already in game instances set.' % game.role)
        elif Game.is_observer_game(game):
            if self.current_observer_type is not None:
                raise exceptions.DiplomacyException('Previous special game %s must be removed before adding new one.'
                                                    % self.current_observer_type)
            self.current_observer_type = game.role
        else:
            assert Game.is_omniscient_game(game)
            if self.current_observer_type is not None:
                raise exceptions.DiplomacyException('Previous special game %s must be removed before adding new one.'
                                                    % self.current_observer_type)
            self.current_observer_type = game.role
        self.games[game.role] = game
