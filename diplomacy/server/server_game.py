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
""" Server game class. """
from diplomacy.engine.game import Game
from diplomacy.engine.message import GLOBAL, Message, OBSERVER, OMNISCIENT, SYSTEM
from diplomacy.engine.power import Power
from diplomacy.utils import exceptions, parsing, strings
from diplomacy.utils.game_phase_data import GamePhaseData

class ServerGame(Game):
    """ ServerGame class.

        Properties:

        - **server**: (optional) server (Server object) that handles this game.
        - **omniscient_usernames** (only for server games):
          set of usernames allowed to be omniscient observers for this game.
        - **moderator_usernames** (only for server games):
          set of usernames allowed to be moderators for this game.
        - **observer** (only for server games):
          special Power object (diplomacy.Power) used to manage observer tokens.
        - **omniscient** (only for server games):
          special Power object (diplomacy.Power) used to manage omniscient tokens.
    """
    __slots__ = ['server', 'omniscient_usernames', 'moderator_usernames', 'observer', 'omniscient']
    model = parsing.update_model(Game.model, {
        strings.MODERATOR_USERNAMES: parsing.DefaultValueType(parsing.SequenceType(str, sequence_builder=set), ()),
        strings.OBSERVER: parsing.OptionalValueType(parsing.JsonableClassType(Power)),
        strings.OMNISCIENT: parsing.OptionalValueType(parsing.JsonableClassType(Power)),
        strings.OMNISCIENT_USERNAMES: parsing.DefaultValueType(parsing.SequenceType(str, sequence_builder=set), ()),
    })

    def __init__(self, server=None, **kwargs):
        # Reference to a Server instance.
        self.server = server                # type: diplomacy.Server
        self.omniscient_usernames = None    # type: set
        self.moderator_usernames = None     # type: set
        self.observer = None                # type: Power
        self.omniscient = None              # type: Power

        super(ServerGame, self).__init__(**kwargs)
        assert self.is_server_game()

        # Initialize special powers.
        self.observer = self.observer or Power(self, name=strings.OBSERVER_TYPE)
        self.omniscient = self.omniscient or Power(self, name=strings.OMNISCIENT_TYPE)
        self.observer.set_controlled(strings.OBSERVER_TYPE)
        self.omniscient.set_controlled(strings.OBSERVER_TYPE)

    # Server-only methods.

    def get_related_power_names(self, power_name):
        """ Return list of power names controlled by the controlled of given power name. """
        related_power_names = []
        if self.has_power(power_name):
            related_power_names = [power_name]
            related_power = self.get_power(power_name)
            if related_power.is_controlled():
                related_power_names = self.get_controlled_power_names(related_power.get_controller())
        return related_power_names

    def filter_phase_data(self, phase_data, role, is_current):
        """ Return a filtered version of given phase data for given gam role.

            :param phase_data: GamePhaseData object to filter.
            :param role: game role to filter phase data for.
            :param is_current: Boolean. Indicate if given phase data is for a current phase (True), or for a pase phase.
            :return: a new GamePhaseData object suitable for given game role.
            :type phase_data: GamePhaseData
        """
        if role == strings.OMNISCIENT_TYPE:
            # Nothing to filter.
            return phase_data
        if role == strings.OBSERVER_TYPE:
            # Filter messages.
            return GamePhaseData(name=phase_data.name,
                                 state=phase_data.state,
                                 orders=phase_data.orders,
                                 results=phase_data.results,
                                 messages=self.filter_messages(phase_data.messages, role))
        # Filter for power roles.
        related_power_names = self.get_related_power_names(role)
        # Filter messages.
        messages = self.filter_messages(phase_data.messages, related_power_names)
        # We filter orders only if phase data is for a current phase.
        if is_current:
            orders = {power_name: phase_data.orders[power_name]
                      for power_name in related_power_names
                      if power_name in phase_data.orders}
        else:
            orders = phase_data.orders
        # results don't need to be filtered: it should be provided empty for current phase,
        # and it should be kept for a past phase/
        return GamePhaseData(name=phase_data.name,
                             state=phase_data.state,
                             orders=orders,
                             messages=messages,
                             results=phase_data.results)

    def game_can_start(self):
        """ Return True if server game can start.
            A game can start if all followings conditions are satisfied:

            - Game has not yet started.
            - Game can start automatically (no rule START_MASTER).
            - Game has expected number of controlled powers.

            :return: a boolean
            :rtype: bool
        """
        return self.is_game_forming and not self.start_master and self.has_expected_controls_count()

    def get_messages(self, game_role, timestamp_from=None, timestamp_to=None):
        """ Return a filtered dict of current messages for given output game role.
            See method filter_messages() about parameters.
        """
        return self.filter_messages(self.messages, game_role, timestamp_from, timestamp_to)

    def get_message_history(self, game_role):
        """ Return a filtered dict of whole message history for given game role. """
        return {str(short_phase): self.filter_messages(messages, game_role)
                for short_phase, messages in self.message_history.items()}

    def get_user_power_names(self, username):
        """ Return list of power names controlled by given user name. """
        return [power.name for power in self.powers.values() if power.is_controlled_by(username)]

    def new_system_message(self, recipient, body):
        """ Create a system message (immediately dated) to be sent by server and add it to message history.
            To be used only by server game.

            :param recipient: recipient description (string). Either:

                - a power name.
                - 'GLOBAL' (all game tokens)
                - 'OBSERVER' (all special tokens [observers and omniscient observers])
                - 'OMNISCIENT' (all omniscient tokens only)

            :param body: message body (string).
            :return: a new GameMessage object.
            :rtype: Message
        """
        assert (recipient in {GLOBAL, OBSERVER, OMNISCIENT}
                or self.has_power(recipient))
        message = Message(phase=self.current_short_phase,
                          sender=SYSTEM,
                          recipient=recipient,
                          message=body)
        # Message timestamp will be generated when adding message.
        self.add_message(message)
        return message

    def as_power_game(self, power_name):
        """ Return a player game data object copy of this game for given power name. """
        for_username = self.get_power(power_name).get_controller()
        game = Game.from_dict(self.to_dict())
        game.error = []
        game.message_history = self.get_message_history(power_name)
        game.messages = self.get_messages(power_name)
        game.phase_abbr = game.current_short_phase
        related_power_names = self.get_related_power_names(power_name)
        for power in game.powers.values():  # type: Power
            power.role = power.name
            power.tokens.clear()
            if power.name not in related_power_names:
                power.vote = strings.NEUTRAL
                power.orders.clear()
        game.role = power_name
        game.controlled_powers = self.get_controlled_power_names(for_username)
        game.observer_level = self.get_observer_level(for_username)
        game.daide_port = self.server.get_daide_port(self.game_id) if self.server else None
        return game

    def as_omniscient_game(self, for_username):
        """ Return an omniscient game data object copy of this game. """
        game = Game.from_dict(self.to_dict())
        game.message_history = self.get_message_history(strings.OMNISCIENT_TYPE)
        game.messages = self.get_messages(strings.OMNISCIENT_TYPE)
        game.phase_abbr = game.current_short_phase
        for power in game.powers.values():  # type: Power
            power.role = strings.OMNISCIENT_TYPE
            power.tokens.clear()
        game.role = strings.OMNISCIENT_TYPE
        game.controlled_powers = self.get_controlled_power_names(for_username)
        game.observer_level = self.get_observer_level(for_username)
        game.daide_port = self.server.get_daide_port(self.game_id) if self.server else None
        return game

    def as_observer_game(self, for_username):
        """ Return an observer game data object copy of this game. """
        game = Game.from_dict(self.to_dict())
        game.error = []
        game.message_history = self.get_message_history(strings.OBSERVER_TYPE)
        game.messages = self.get_messages(strings.OBSERVER_TYPE)
        game.phase_abbr = game.current_short_phase
        for power in game.powers.values():  # type: Power
            power.role = strings.OBSERVER_TYPE
            power.tokens.clear()
            power.vote = strings.NEUTRAL
        game.role = strings.OBSERVER_TYPE
        game.controlled_powers = self.get_controlled_power_names(for_username)
        game.observer_level = self.get_observer_level(for_username)
        game.daide_port = self.server.get_daide_port(self.game_id) if self.server else None
        return game

    def cast(self, role, for_username):
        """ Return a copy of this game for given role
            (either observer role, omniscient role or a power role).
        """
        assert strings.role_is_special(role) or self.has_power(role)
        if role == strings.OBSERVER_TYPE:
            return self.as_observer_game(for_username)
        if role == strings.OMNISCIENT_TYPE:
            return self.as_omniscient_game(for_username)
        return self.as_power_game(role)

    def is_controlled_by(self, power_name, username):
        """ (for server game) Return True if given power name is controlled by given username. """
        return self.get_power(power_name).is_controlled_by(username)

    def get_observer_level(self, username):
        """ Return the highest observation level allowed for given username.

            :param username: name of user to get observation right
            :return: either 'master_type', 'omniscient_type', 'observer_type' or None.
        """
        if (self.server and self.server.users.has_admin(username)) or self.is_moderator(username):
            return strings.MASTER_TYPE
        if self.is_omniscient(username):
            return strings.OMNISCIENT_TYPE
        if not self.no_observations:
            return strings.OBSERVER_TYPE
        return None

    def get_reception_addresses(self):
        """ Generate addresses (couple [power name, token]) of all users implied in this game. """
        for power in self.powers.values():  # type: Power
            for token in power.tokens:
                yield (power.name, token)
        for token in self.observer.tokens:
            yield (self.observer.name, token)
        for token in self.omniscient.tokens:
            yield (self.omniscient.name, token)

    def get_special_addresses(self):
        """ Generate addresses (couples [power name, token]) of
            omniscient observers and simple observers of this game.
        """
        for power in (self.omniscient, self.observer):
            for token in power.tokens:
                yield (power.name, token)

    def get_observer_addresses(self):
        """ Generate addresses (couples [power name, token]) of observers of this game. """
        for token in self.observer.tokens:
            yield (self.observer.name, token)

    def get_omniscient_addresses(self):
        """ Generate addresses (couples [power name, token])
            of omniscient observers of this game.
        """
        for token in self.omniscient.tokens:
            yield (self.omniscient.name, token)

    def get_special_token_role(self, token):
        """ Return role name (either OBSERVER_TYPE or OMNISCIENT_TYPE) for given special token. """
        if self.has_omniscient_token(token):
            return strings.OMNISCIENT_TYPE
        if self.has_observer_token(token):
            return strings.OBSERVER_TYPE
        raise exceptions.DiplomacyException('Unknown special token in game %s' % self.game_id)

    def get_power_addresses(self, power_name):
        """ Generate addresses (couples [power name, token])
            of user controlling given power name.
        """
        for token in self.get_power(power_name).tokens:
            yield (power_name, token)

    def has_player(self, username):
        """ (for server game) Return True if given username controls any map power. """
        return any(power.is_controlled_by(username) for power in self.powers.values())

    def has_token(self, token):
        """ Return True if game has given token (either observer, omniscient or player). """
        return self.omniscient.has_token(token) or self.observer.has_token(token) or any(
            power.has_token(token) for power in self.powers.values())

    def has_observer_token(self, token):
        """ Return True if game has given observer token. """
        return self.observer.has_token(token)

    def has_omniscient_token(self, token):
        """ Return True if game has given omniscient observer token. """
        return self.omniscient.has_token(token)

    def has_player_token(self, token):
        """ Return True if game has given player token. """
        return any(power.has_token(token) for power in self.powers.values())

    def power_has_token(self, power_name, token):
        """ Return True if given power has given player token.

            :param power_name: name of power to check.
            :param token: token to look for.
            :return: a boolean
        """
        return self.get_power(power_name).has_token(token)

    def add_omniscient_token(self, token):
        """ Set given token as omniscient token. """
        if self.observer.has_token(token):
            raise exceptions.ResponseException('Token already registered as observer.')
        if self.has_player_token(token):
            raise exceptions.ResponseException('Token already registered as player.')
        self.omniscient.add_token(token)

    def add_observer_token(self, token):
        """ Set given token as observer token. """
        if self.omniscient.has_token(token):
            raise exceptions.ResponseException('Token already registered as omniscient.')
        if self.has_player_token(token):
            raise exceptions.ResponseException('Token already registered as player.')
        self.observer.add_token(token)

    def transfer_special_token(self, token):
        """ Move given token from a special case to another
            (observer -> omniscient or omniscient -> observer).
        """
        if self.has_observer_token(token):
            self.remove_observer_token(token)
            self.add_omniscient_token(token)
        elif self.has_omniscient_token(token):
            self.remove_omniscient_token(token)
            self.add_observer_token(token)

    def control(self, power_name, username, token):
        """ Control given power name with given username via given token. """
        if self.observer.has_token(token):
            raise exceptions.ResponseException('Token already registered as observer.')
        if self.omniscient.has_token(token):
            raise exceptions.ResponseException('Token already registered as omniscient.')
        power = self.get_power(power_name)  # type: Power
        if power.is_controlled() and not power.is_controlled_by(username):
            raise exceptions.ResponseException('Power already controlled by another user.')
        power.set_controlled(username)
        power.add_token(token)

    def remove_observer_token(self, token):
        """ Remove given observer token. """
        self.observer.remove_tokens([token])

    def remove_omniscient_token(self, token):
        """ Remove given omniscient token. """
        self.omniscient.remove_tokens([token])

    def remove_special_token(self, special_name, token):
        """ Remove given token from given special power name
            (either __OBSERVER__ or __OMNISCIENT__).
        """
        if special_name == self.observer.name:
            self.remove_observer_token(token)
        else:
            assert special_name == self.omniscient.name
            self.remove_omniscient_token(token)

    def remove_all_tokens(self):
        """ Remove all connected tokens from this game. """
        self.observer.tokens.clear()
        self.omniscient.tokens.clear()
        for power in self.powers.values():
            power.tokens.clear()

    def remove_token(self, token):
        """ Remove token from this game. """
        for power in self.powers.values():  # type: Power
            power.remove_tokens([token])
        for special_power in (self.observer, self.omniscient):
            special_power.remove_tokens([token])

    def is_moderator(self, username):
        """ Return True if given username is a moderator of this game. """
        return username in self.moderator_usernames

    def is_omniscient(self, username):
        """ Return True if given username is allowed to be an omniscient observer of this game. """
        return username in self.omniscient_usernames

    def promote_moderator(self, username):
        """ Allow given username to be a moderator of this game. """
        self.moderator_usernames.add(username)

    def promote_omniscient(self, username):
        """ Allow given username to be an omniscient observer of this game. """
        self.omniscient_usernames.add(username)

    def demote_moderator(self, username):
        """ Remove given username from allowed moderators. """
        if username in self.moderator_usernames:
            self.moderator_usernames.remove(username)

    def demote_omniscient(self, username):
        """ Remove given username from allowed omniscient observers. """
        if username in self.omniscient_usernames:
            self.omniscient_usernames.remove(username)

    def filter_usernames(self, filter_function):
        """ Remove each omniscient username, moderator username and player controller
            that does not match given filter function (if filter_function(username) is False).

            :param filter_function: a callable receiving a username and returning a boolean.
            :return: an integer, either:

                * 0: nothing changed.
                * -1: something changed, but no player controllers removed.
                * 1: something changed, and some player controllers were removed.

                So, if 1 is returned, there are new dummy powers in the game
                (some notifications may need to be sent).

        """
        n_kicked_players = 0
        n_kicked_omniscients = len(self.omniscient_usernames)
        n_kicked_moderators = len(self.moderator_usernames)
        self.omniscient_usernames = set(username for username in self.omniscient_usernames if filter_function(username))
        self.moderator_usernames = set(username for username in self.moderator_usernames if filter_function(username))
        for power in self.powers.values():
            if power.is_controlled() and not filter_function(power.get_controller()):
                power.set_controlled(None)
                n_kicked_players += 1
        n_kicked_omniscients -= len(self.omniscient_usernames)
        n_kicked_moderators -= len(self.moderator_usernames)
        if n_kicked_players:
            return 1
        if n_kicked_moderators or n_kicked_omniscients:
            return -1
        return 0

    def filter_tokens(self, filter_function):
        """ Remove from this game any token not matching given filter function
            (if filter_function(token) is False).
        """
        self.observer.remove_tokens([token for token in self.observer.tokens if not filter_function(token)])
        self.omniscient.remove_tokens([token for token in self.omniscient.tokens if not filter_function(token)])
        for power in self.powers.values():  # type: Power
            power.remove_tokens([token for token in power.tokens if not filter_function(token)])

    def process(self):
        """ Process current game phase and move forward to next phase.

            :return: a triple containing:

                - previous game state (before the processing)
                - current game state (after processing and game updates)
                - A dictionary mapping kicked power names to tokens previously associated to these powers.
                  Useful to notify kicked users as they will be not registered in game anymore.

                If game was not active, triple is (None, None, None).

                If game kicked powers, only kicked powers dict is returned: (None, None, kicked powers).

                If game was correctly processed, only states are returned: (prev, curr, None).
        """
        if not self.is_game_active:
            return None, None, None
        # Kick powers if necessary.
        all_orderable_locations = self.get_orderable_locations()
        kicked_powers = {}
        for power in self.powers.values():
            if (power.is_controlled()
                    and not power.order_is_set
                    and not self.civil_disorder
                    and all_orderable_locations[power.name]):
                # This controlled power has not submitted orders, we have not rule CIVIL_DISORDER,
                # and this power WAS allowed to submit orders for this phase.
                # We kick such power.
                kicked_powers[power.name] = set(power.tokens)
                power.set_controlled(None)

        if kicked_powers:
            # Some powers were kicked from an active game before processing.
            # This game must be stopped and cannot be processed. We return info about kicked powers.
            self.set_status(strings.FORMING)
            return None, None, kicked_powers

        # Process game and retrieve previous state.
        previous_phase_data = super(ServerGame, self).process()
        if self.count_controlled_powers() < self.get_expected_controls_count():
            # There is no more enough controlled powers, we should stop game.
            self.set_status(strings.FORMING)

        # Return process results: previous phase data, current phase data, and None for no kicked powers.
        return previous_phase_data, self.get_phase_data(), None
