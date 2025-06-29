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
""" Concrete standalone server object. Manages and save server data and games on disk,
    send notifications, receives requests and send responses.

    Example:

    .. code-block:: python

        >>> from diplomacy import Server
        >>> Server().start(port=1234)  # If port is not given, a random port will be selected.

    You can interrupt server by sending a keyboard interrupt signal (Ctrl+C).

    .. code-block:: python

        >>> from diplomacy import Server
        >>> try:
        >>>     Server().start()
        >>> except KeyboardInterrupt:
        >>>     print('Server interrupted.')

    You can also configure some server attributes when instantiating it:

    .. code-block:: python

        >>> from diplomacy import Server
        >>> server = Server(backup_delay_seconds=5)
        >>> server.start()

    These are public configurable server attributes. They are saved on disk at each server backup:

    - **allow_user_registrations**: (bool) indicate if server accepts users registrations (default True)
    - **backup_delay_seconds**: (int) number of seconds to wait between two consecutive full server backup
      on disk (default 10 minutes)
    - **ping_seconds**: (int) ping period used by server to check is connected sockets are alive.
    - **max_games**: (int) maximum number of games server accepts to create.
      If there are at least such number of games on server, server will not accept
      further game creation requests. If 0, no limit. (default 0)
    - **remove_canceled_games**: (bool) indicate if games must be deleted from server database
      when they are canceled (default False)

"""
import atexit
import base64
import logging
import os
from random import randint
import socket
import signal
from typing import Dict, Set, List

import tornado
import tornado.web
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado.queues import Queue
from tornado.websocket import WebSocketClosedError

import ujson as json

import diplomacy.settings
from diplomacy.communication import notifications
from diplomacy.daide.server import Server as DaideServer
from diplomacy.server.connection_handler import ConnectionHandler
from diplomacy.server.notifier import Notifier
from diplomacy.server.scheduler import Scheduler
from diplomacy.server.server_game import ServerGame
from diplomacy.server.users import Users
from diplomacy.engine.map import Map
from diplomacy.utils import common, exceptions, strings, constants

LOGGER = logging.getLogger(__name__)

def is_port_opened(port, hostname='127.0.0.1'):
    """ Checks if the specified port is opened

        :param port: The port to check
        :param hostname: The hostname to check, defaults to '127.0.0.1'
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sock.connect_ex((hostname, port)) == 0:
        return True
    return False

def get_absolute_path(directory=None):
    """ Return absolute path of given directory.
        If given directory is None, return absolute path of current directory.
    """
    return os.path.abspath(directory or os.getcwd())

def get_backup_filename(filename):
    """ Return a backup filename from given filename (given filename with a special suffix). """
    return '%s.backup' % filename

def save_json_on_disk(filename, json_dict):
    """ Save given JSON dictionary into given filename and back-up previous file version if exists. """
    if os.path.exists(filename):
        os.rename(filename, get_backup_filename(filename))
    with open(filename, 'w') as file:
        json.dump(json_dict, file)

def load_json_from_disk(filename):
    """ Return a JSON dictionary loaded from given filename.
        If JSON parsing fail for given filename, try to load JSON dictionary for a backup file
        (if present) and rename backup file to given filename
        (backup file becomes current file versions).

        :param filename: file path to open
        :return: JSON dictionary loaded from file
        :rtype: dict
    """
    try:
        with open(filename, 'rb') as file:
            json_dict = json.load(file)
    except ValueError as exception:
        backup_filename = get_backup_filename(filename)
        if not os.path.isfile(backup_filename):
            raise exception
        with open(backup_filename, 'rb') as backup_file:
            json_dict = json.load(backup_file)
        os.rename(backup_filename, filename)
    return json_dict

def ensure_path(folder_path):
    """ Make sure given folder path exists and return given path.
        Raises an exception if path does not exists, cannot be created or is not a folder.
    """
    if not os.path.exists(folder_path):
        LOGGER.info('Creating folder %s', folder_path)
        os.makedirs(folder_path, exist_ok=True)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise exceptions.FolderException(folder_path)
    return folder_path

class InterruptionHandler():
    """ Helper class used to save server when a system interruption signal is sent (e.g. KeyboardInterrupt). """
    __slots__ = ['server', 'previous_handler']

    def __init__(self, server):
        """ Initializer the handler.

            :param server: server to save
        """
        self.server = server  # type: Server
        self.previous_handler = signal.getsignal(signal.SIGINT)

    def handler(self, signum, frame):
        """ Handler function.

            :param signum: system signal received
            :param frame: frame received
        """
        if signum == signal.SIGINT:
            self.server.stop_daide_server(None)
            self.server.backup_now(force=True)
            if self.previous_handler:
                self.previous_handler(signum, frame)

class _ServerBackend:
    """ Class representing tornado objects used to run a server.

        Properties:

        - **port**: (integer) port where server runs.
        - **application**: tornado web Application object.
        - **http_server**: tornado HTTP server object running server code.
        - **io_loop**: tornado IO loop where server runs.
    """
    #pylint: disable=too-few-public-methods
    __slots__ = ['port', 'application', 'http_server', 'io_loop']


    def __init__(self):
        """ Initialize server backend. """
        self.port = None
        self.application = None
        self.http_server = None
        self.io_loop = None

class Server:
    """ Server class. """
    __slots__ = ['data_path', 'games_path', 'available_maps', 'maps_mtime', 'notifications',
                 'games_scheduler', 'allow_registrations', 'max_games', 'remove_canceled_games', 'users', 'games',
                 'daide_servers', 'backup_server', 'backup_games', 'backup_delay_seconds', 'ping_seconds',
                 'interruption_handler', 'backend', 'games_with_dummy_powers', 'dispatched_dummy_powers']

    # Servers cache.
    __cache__ = {}  # {absolute path of working folder => Server}

    def __new__(cls, server_dir=None, **kwargs):
        #pylint: disable=unused-argument
        server_dir = get_absolute_path(server_dir)
        if server_dir in cls.__cache__:
            server = cls.__cache__[server_dir]
        else:
            server = object.__new__(cls)
        return server

    def __init__(self, server_dir=None, **kwargs):
        """ Initialize the server.
            Server data is stored in folder ``<working directory>/data``.

            :param server_dir: path of folder in (from) which server data will be saved (loaded).
                If None, working directory (where script is executed) will be used.
            :param kwargs: (optional) values for some public configurable server attributes.
                Given values will overwrite values saved on disk.
        """

        # File paths and attributes related to database.
        server_dir = get_absolute_path(server_dir)
        if server_dir in self.__class__.__cache__:
            return
        if not os.path.exists(server_dir) or not os.path.isdir(server_dir):
            raise exceptions.ServerDirException(server_dir)
        self.data_path = os.path.join(server_dir, 'data')
        self.games_path = os.path.join(self.data_path, 'games')

        # Data in memory (not stored on disk).
        self.notifications = Queue()
        self.games_scheduler = Scheduler(1, self._process_game)
        self.backup_server = None
        self.backup_games = {}
        self.interruption_handler = InterruptionHandler(self)
        # Backend objects used to run server. If None, server is not yet started.
        # Initialized when you call Server.start() (see method below).
        self.backend = None  # type: _ServerBackend

        # Database (stored on disk).
        self.allow_registrations = True
        self.max_games = 0
        self.remove_canceled_games = False
        self.backup_delay_seconds = constants.DEFAULT_BACKUP_DELAY_SECONDS
        self.ping_seconds = constants.DEFAULT_PING_SECONDS
        self.users = None  # type: Users  # Users and administrators usernames.
        self.available_maps = {}  # type: Dict[str, List[str]] # {"map_name" => list("map_power")}
        self.maps_mtime = 0  # Latest maps modification date (used to manage maps cache in server object).

        # Server games loaded on memory (stored on disk).
        # Saved separately (each game in one JSON file).
        # Each game also stores tokens connected (player tokens, observer tokens, omniscient tokens).
        self.games = {}  # type: Dict[str, ServerGame]

        # Dictionary mapping game ID to list of power names.
        self.games_with_dummy_powers = {}  # type: Dict[str, List[str]]

        # Dictionary mapping a game ID present in games_with_dummy_powers, to
        # a couple of associated bot token and time when bot token was associated to this game ID.
        # If there is no bot token associated, couple is (None, None).
        self.dispatched_dummy_powers = {} # type: dict{str, tuple}

        # DAIDE TCP servers listening to a game's dedicated port.
        self.daide_servers = {}             # {port: daide_server}

        # Load data on memory.
        self._load()

        # If necessary, updated server configurable attributes from kwargs.
        self.allow_registrations = bool(kwargs.pop(strings.ALLOW_REGISTRATIONS, self.allow_registrations))
        self.max_games = int(kwargs.pop(strings.MAX_GAMES, self.max_games))
        self.remove_canceled_games = bool(kwargs.pop(strings.REMOVE_CANCELED_GAMES, self.remove_canceled_games))
        self.backup_delay_seconds = int(kwargs.pop(strings.BACKUP_DELAY_SECONDS, self.backup_delay_seconds))
        self.ping_seconds = int(kwargs.pop(strings.PING_SECONDS, self.ping_seconds))
        assert not kwargs
        LOGGER.debug('Ping        : %s', self.ping_seconds)
        LOGGER.debug('Backup delay: %s', self.backup_delay_seconds)

        # Add server on servers cache.
        self.__class__.__cache__[server_dir] = self

    @property
    def port(self):
        """ Property: return port where this server currently runs, or None if server is not yet started. """
        return self.backend.port if self.backend else None

    def _load_available_maps(self):
        """ Load a dictionary (self.available_maps) mapping every map name to a dict of map info.
            for all maps available in diplomacy package.
        """
        diplomacy_map_dir = os.path.join(diplomacy.settings.PACKAGE_DIR, strings.MAPS)
        new_maps_mtime = self.maps_mtime
        for filename in os.listdir(diplomacy_map_dir):
            if filename.endswith('.map'):
                map_filename = os.path.join(diplomacy_map_dir, filename)
                map_mtime = os.path.getmtime(map_filename)
                map_name = filename[:-4]
                if map_name not in self.available_maps or map_mtime > self.maps_mtime:
                    # Either it's a new map file or map file was modified.
                    available_map = Map(map_name)
                    self.available_maps[map_name] = {
                        'powers': list(available_map.powers),
                        'supply_centers': list(available_map.scs),
                        'loc_type': available_map.loc_type.copy(),
                        'loc_abut': available_map.loc_abut.copy(),
                        'aliases': available_map.aliases.copy()
                    }
                    new_maps_mtime = max(new_maps_mtime, map_mtime)
        self.maps_mtime = new_maps_mtime

    def _get_server_data_filename(self):
        """ Return path to server data file name (server.json, making sure that data folder exists.
            Raises an exception if data folder does not exists and cannot be created.
        """
        return os.path.join(ensure_path(self.data_path), 'server.json')

    def _load(self):
        """ Load database from disk. """
        LOGGER.info("Loading database.")
        ensure_path(self.data_path)                                 # <server dir>/data
        ensure_path(self.games_path)                                # <server dir>/data/games
        server_data_filename = self._get_server_data_filename()     # <server dir>/data/server.json
        if os.path.exists(server_data_filename):
            LOGGER.info("Loading server.json.")
            server_info = load_json_from_disk(server_data_filename)
            self.allow_registrations = server_info[strings.ALLOW_REGISTRATIONS]
            self.backup_delay_seconds = server_info[strings.BACKUP_DELAY_SECONDS]
            self.ping_seconds = server_info[strings.PING_SECONDS]
            self.max_games = server_info[strings.MAX_GAMES]
            self.remove_canceled_games = server_info[strings.REMOVE_CANCELED_GAMES]
            self.users = Users.from_dict(server_info[strings.USERS])
            self.available_maps = server_info[strings.AVAILABLE_MAPS]
            self.maps_mtime = server_info[strings.MAPS_MTIME]
            # games and map are loaded from disk.
        else:
            LOGGER.info("Creating server.json.")
            self.users = Users()
            self.backup_now(force=True)
        # Add default accounts.
        for (username, password) in (
                ('admin', 'password'),
                (constants.PRIVATE_BOT_USERNAME, constants.PRIVATE_BOT_PASSWORD)
        ):
            if not self.users.has_username(username):
                self.users.add_user(username, common.hash_password(password))
        # Set default admin account.
        self.users.add_admin('admin')

        self._load_available_maps()

        LOGGER.info('Server loaded.')

    def _backup_server_data_now(self, force=False):
        """ Save latest backed-up version of server data on disk. This does not save games.

            :param force: if True, force to save current server data,
                even if it was not modified recently.
        """
        if force:
            self.save_data()
        if self.backup_server:
            save_json_on_disk(self._get_server_data_filename(), self.backup_server)
            self.backup_server = None
            LOGGER.info("Saved server.json.")

    def _backup_games_now(self, force=False):
        """ Save latest backed-up versions of loaded games on disk.

            :param force: if True, force to save all games currently loaded in memory
                even if they were not modified recently.
        """
        ensure_path(self.games_path)
        if force:
            for server_game in self.games.values():
                self.save_game(server_game)
        for game_id, game_dict in self.backup_games.items():
            game_path = os.path.join(self.games_path, '%s.json' % game_id)
            save_json_on_disk(game_path, game_dict)
            LOGGER.info('Game data saved: %s', game_id)
        self.backup_games.clear()

    def backup_now(self, force=False):
        """ Save backup of server data and loaded games immediately.

            :param force: if True, force to save server data and all loaded games
                even if there are no recent changes.
        """
        self._backup_server_data_now(force=force)
        self._backup_games_now(force=force)

    @gen.coroutine
    def _process_game(self, server_game):
        """ Process given game and send relevant notifications.

            :param server_game: server game to process
            :return: A boolean indicating if we must stop game.
            :type server_game: ServerGame
        """
        LOGGER.debug('Processing game %s (status %s).', server_game.game_id, server_game.status)
        previous_phase_data, current_phase_data, kicked_powers = server_game.process()
        self.save_game(server_game)

        if previous_phase_data is None and kicked_powers is None:
            # Game must be unscheduled immediately.
            return True

        notifier = Notifier(self)

        if kicked_powers:
            # Game was not processed because of kicked powers.
            # We notify those kicked powers and game must be unscheduled immediately.
            kicked_addresses = [(power_name, token)
                                for (power_name, tokens) in kicked_powers.items()
                                for token in tokens]
            # Notify kicked players.
            notifier.notify_game_addresses(
                server_game.game_id,
                kicked_addresses,
                notifications.PowersControllers,
                powers=server_game.get_controllers(),
                timestamps=server_game.get_controllers_timestamps()
            )
            return True

        # Game was processed normally.
        # Send game updates to powers, observers and omniscient observers.
        yield notifier.notify_game_processed(server_game, previous_phase_data, current_phase_data)

        # If game is completed, we must close associated DAIDE port.
        if server_game.is_game_done:
            self.stop_daide_server(server_game.game_id)

        # Game must be stopped if not active.
        return not server_game.is_game_active

    @gen.coroutine
    def _task_save_database(self):
        """ IO loop callable: save database and loaded games periodically.
            Data to save are checked every BACKUP_DELAY_SECONDS seconds.
        """
        LOGGER.info('Waiting for save events.')
        while True:
            yield gen.sleep(self.backup_delay_seconds)
            self.backup_now()

    @gen.coroutine
    def _task_send_notifications(self):
        """ IO loop callback: consume notifications and send it. """
        LOGGER.info('Waiting for notifications to send.')
        while True:
            connection_handler, notification = yield self.notifications.get()
            try:
                yield connection_handler.write_message(notification)
            except WebSocketClosedError:
                LOGGER.error('Websocket was closed while sending a notification.')
            except StreamClosedError:
                LOGGER.error('Stream was closed while sending a notification.')
            finally:
                self.notifications.task_done()

    def set_tasks(self, io_loop: IOLoop):
        """ Set server callbacks on given IO loop.
            Must be called once per server before starting IO loop.
        """
        io_loop.add_callback(self._task_save_database)
        io_loop.add_callback(self._task_send_notifications)
        # These both coroutines are used to manage games.
        io_loop.add_callback(self.games_scheduler.process_tasks)
        io_loop.add_callback(self.games_scheduler.schedule)
        # Set callback on KeyboardInterrupt.
        signal.signal(signal.SIGINT, self.interruption_handler.handler)
        atexit.register(self.backup_now)

    def start(self, port=None, io_loop=None):
        """ Start server if not yet started. Raise an exception if server is already started.

            :param port: (optional) port where server must run. If not provided,
                try to start on a random selected port. Use property `port` to get current server port.
            :param io_loop: (optional) tornado IO lopp where server must run. If not provided, get
                default IO loop instance (tornado.ioloop.IOLoop.instance()).
        """
        if self.backend is not None:
            raise exceptions.DiplomacyException('Server is already running on port %s.' % self.backend.port)
        if port is None:
            port = 8432
        if io_loop is None:
            io_loop = tornado.ioloop.IOLoop.instance()
        handlers = [
            tornado.web.url(r"/", ConnectionHandler, {'server': self}),
        ]
        settings = {
            'cookie_secret': common.generate_token(),
            'xsrf_cookies': True,
            'websocket_ping_interval': self.ping_seconds,
            'websocket_ping_timeout': 2 * self.ping_seconds,
            'websocket_max_message_size': 64 * 1024 * 1024
        }
        self.backend = _ServerBackend()
        self.backend.application = tornado.web.Application(handlers, **settings)
        self.backend.http_server = self.backend.application.listen(port)
        self.backend.io_loop = io_loop
        self.backend.port = port
        self.set_tasks(io_loop)
        LOGGER.info('Running on port %d', self.backend.port)
        if not io_loop.asyncio_loop.is_running():
            io_loop.start()

    def get_game_indices(self):
        """ Iterate over all game indices in server database.
            Convenient method to iterate over all server games (by calling load_game() on each game index).
        """
        for game_id in self.games:
            yield game_id
        if os.path.isdir(self.games_path):
            for filename in os.listdir(self.games_path):
                if filename.endswith('.json'):
                    game_id = filename[:-5]
                    if game_id not in self.games:
                        yield game_id

    def count_server_games(self):
        """ Return number of server games in server database. """
        count = 0
        if os.path.isdir(self.games_path):
            for filename in os.listdir(self.games_path):
                if filename.endswith('.json'):
                    count += 1
        return count

    def save_data(self):
        """ Update on-memory backup of server data. """
        self.backup_server = {
            strings.ALLOW_REGISTRATIONS: self.allow_registrations,
            strings.BACKUP_DELAY_SECONDS: self.backup_delay_seconds,
            strings.PING_SECONDS: self.ping_seconds,
            strings.MAX_GAMES: self.max_games,
            strings.REMOVE_CANCELED_GAMES: self.remove_canceled_games,
            strings.USERS: self.users.to_dict(),
            strings.AVAILABLE_MAPS: self.available_maps,
            strings.MAPS_MTIME: self.maps_mtime,
        }

    def save_game(self, server_game):
        """ Update on-memory version of given server game.

            :param server_game: server game
            :type server_game: ServerGame
        """
        self.backup_games[server_game.game_id] = server_game.to_dict()
        # Check dummy powers for a game every time we have to save it.
        self.register_dummy_power_names(server_game)

    def register_dummy_power_names(self, server_game):
        """ Update internal registry of dummy power names waiting for orders for given server games.

            :param server_game: server game to check
            :type server_game: ServerGame
        """
        if server_game.map.root_map != 'standard':
            # Bot does not currently support other maps.
            return
        dummy_power_names = []
        if server_game.is_game_active or server_game.is_game_paused:
            dummy_power_names = server_game.get_dummy_unordered_power_names()
            if dummy_power_names:
                # Update registry of dummy powers.
                self.games_with_dummy_powers[server_game.game_id] = dummy_power_names
                # Every time we update registry of dummy powers,
                # then we also update bot time in registry of dummy powers associated to bot tokens.
                bot_token, _ = self.dispatched_dummy_powers.get(server_game.game_id, (None, None))
                self.dispatched_dummy_powers[server_game.game_id] = (bot_token, common.timestamp_microseconds())
        if not dummy_power_names:
            # No waiting dummy powers for this game, or game is not playable (canceled, completed, or forming).
            self.games_with_dummy_powers.pop(server_game.game_id, None)
            self.dispatched_dummy_powers.pop(server_game.game_id, None)

    def get_dummy_waiting_power_names(self, buffer_size, bot_token):
        """ Return names of dummy powers waiting for orders for current loaded games.
            This query is allowed only for bot tokens.

            :param buffer_size: maximum number of powers queried.
            :param bot_token: bot token
            :return: a dictionary mapping each game ID to a list of power names.
        """
        if self.users.get_name(bot_token) != constants.PRIVATE_BOT_USERNAME:
            raise exceptions.ResponseException('Invalid bot token %s' % bot_token)
        selected_size = 0
        selected_games = {}
        for game_id in sorted(list(self.games_with_dummy_powers.keys())):
            registered_token, registered_time = self.dispatched_dummy_powers[game_id]
            if registered_token is not None:
                time_elapsed_seconds = (common.timestamp_microseconds() - registered_time) / 1000000
                if time_elapsed_seconds > constants.PRIVATE_BOT_TIMEOUT_SECONDS or registered_token == bot_token:
                    # This game still has dummy powers but, either time allocated to previous bot token is over,
                    # or bot dedicated to this game is asking for current dummy powers of this game.
                    # Forget previous bot token.
                    registered_token = None
            if registered_token is None:
                # This game is not associated to any bot token.
                # Let current bot token handle it if buffer size is not reached.
                dummy_power_names = self.games_with_dummy_powers[game_id]
                nb_powers = len(dummy_power_names)
                if selected_size + nb_powers > buffer_size:
                    # Buffer size would be exceeded. We stop to collect games now.
                    break
                # Otherwise we collect this game.
                selected_games[game_id] = dummy_power_names
                selected_size += nb_powers
                self.dispatched_dummy_powers[game_id] = (bot_token, common.timestamp_microseconds())
        return selected_games

    def has_game_id(self, game_id):
        """ Return True if server database contains such game ID. """
        if game_id in self.games:
            return True
        expected_game_path = os.path.join(self.games_path, '%s.json' % game_id)
        return os.path.exists(expected_game_path) and os.path.isfile(expected_game_path)

    def load_game(self, game_id):
        """ Return a game matching given game ID from server database.
            Raise an exception if such game does not exists.

            If such game is already stored in server object, return it.

            Else, load it from disk but **does not store it in server object**.

            To load and immediately store a game object in server object, please use method get_game().

            Method load_game() is convenient when you want to iterate over all games in server database
            without taking memory space.

            :param game_id: ID of game to load.
            :return: a ServerGame object
            :rtype: ServerGame
        """
        if game_id in self.games:
            return self.games[game_id]
        game_filename = os.path.join(ensure_path(self.games_path), '%s.json' % game_id)
        if not os.path.isfile(game_filename):
            raise exceptions.GameIdException()
        try:
            server_game = ServerGame.from_dict(load_json_from_disk(game_filename))  # type: ServerGame
            server_game.server = self
            server_game.filter_usernames(self.users.has_username)
            server_game.filter_tokens(self.users.has_token)
            return server_game
        except ValueError as exc:
            # Error occurred while parsing JSON file: bad JSON file.
            try:
                os.remove(game_filename)
            finally:
                # This should be an internal server error.
                raise exc

    def add_new_game(self, server_game):
        """ Add a new game data on server in memory and perform any addition processing.
            This does not save the game on disk.

            :type server_game: ServerGame
        """
        # Register game on memory.
        self.games[server_game.game_id] = server_game
        # Start DAIDE server for this game.
        self.start_new_daide_server(server_game.game_id)

    def get_game(self, game_id):
        """ Return game saved on server matching given game ID.
            Raise an exception if game ID not found.
            Return game if already loaded on memory, else load it from disk, store it,
            perform any loading/addition processing and return it.

            :param game_id: ID of game to load.
            :return: a ServerGame object.
            :rtype: ServerGame
        """
        server_game = self.load_game(game_id)
        if game_id not in self.games:
            LOGGER.debug('Game loaded: %s', game_id)
            # Check dummy powers for this game as soon as it's loaded from disk.
            self.register_dummy_power_names(server_game)
            # Register game on memory.
            self.games[server_game.game_id] = server_game
            # Start DAIDE server for this game.
            self.start_new_daide_server(server_game.game_id)
            # We have just loaded game from disk. Start it if necessary.
            if not server_game.start_master and server_game.has_expected_controls_count():
                # We may have to start game.
                if server_game.does_not_wait():
                    # We must process game.
                    server_game.process()
                    self.save_game(server_game)
                # Game must be scheduled only if active.
                if server_game.is_game_active:
                    LOGGER.debug('Game loaded and scheduled: %s', server_game.game_id)
                    self.schedule_game(server_game)
        return server_game

    def delete_game(self, server_game):
        """ Delete given game from server (both from memory and disk)
            and perform any post-deletion processing.

            :param server_game: game to delete
            :type server_game: ServerGame
        """
        if not (server_game.is_game_canceled or server_game.is_game_completed):
            server_game.set_status(strings.CANCELED)
        game_filename = os.path.join(self.games_path, '%s.json' % server_game.game_id)
        backup_game_filename = get_backup_filename(game_filename)
        if os.path.isfile(game_filename):
            os.remove(game_filename)
        if os.path.isfile(backup_game_filename):
            os.remove(backup_game_filename)
        self.games.pop(server_game.game_id, None)
        self.backup_games.pop(server_game.game_id, None)
        self.games_with_dummy_powers.pop(server_game.game_id, None)
        self.dispatched_dummy_powers.pop(server_game.game_id, None)
        # Stop DAIDE server associated to this game.
        self.stop_daide_server(server_game.game_id)

    @gen.coroutine
    def schedule_game(self, server_game):
        """ Add a game to scheduler only if game has a deadline and is not already scheduled.
            To add games without deadline, use force_game_processing().

            :param server_game: game
            :type server_game: ServerGame
        """
        if not (yield self.games_scheduler.has_data(server_game)) and server_game.deadline:
            yield self.games_scheduler.add_data(server_game, server_game.deadline)

    @gen.coroutine
    def unschedule_game(self, server_game):
        """ Remove a game from scheduler.

            :param server_game: game
            :type server_game: ServerGame
        """
        if (yield self.games_scheduler.has_data(server_game)):
            yield self.games_scheduler.remove_data(server_game)

    @gen.coroutine
    def force_game_processing(self, server_game):
        """ Add a game to scheduler to be processed as soon as possible.
            Use this method instead of schedule_game() to explicitly add games with null deadline.

            :param server_game: game
            :type server_game: ServerGame
        """
        yield self.games_scheduler.no_wait(server_game, server_game.deadline, lambda g: g.does_not_wait())

    def start_game(self, server_game):
        """ Start given server game.

            :param server_game: server game
            :type server_game: ServerGame
        """
        server_game.set_status(strings.ACTIVE)
        self.schedule_game(server_game)
        Notifier(self).notify_game_status(server_game)

    def stop_game_if_needed(self, server_game):
        """ Stop game if it has not required number of controlled powers.
            Notify game if status changed.

            :param server_game: game to check
            :param server_game: game
            :type server_game: ServerGame
        """
        if server_game.is_game_active and (
                server_game.count_controlled_powers() < server_game.get_expected_controls_count()):
            server_game.set_status(strings.FORMING)
            self.unschedule_game(server_game)
            Notifier(self).notify_game_status(server_game)

    def user_is_master(self, username, server_game):
        """ Return True if given username is a game master for given game data.

            :param username: username
            :param server_game: game data
            :return: a boolean
            :type server_game: ServerGame
            :rtype: bool
        """
        return self.users.has_admin(username) or server_game.is_moderator(username)

    def user_is_omniscient(self, username, server_game):
        """ Return True if given username is omniscient for given game data.

            :param username: username
            :param server_game: game data
            :return: a boolean
            :type server_game: ServerGame
            :rtype: bool
        """
        return (self.users.has_admin(username)
                or server_game.is_moderator(username)
                or server_game.is_omniscient(username))

    def token_is_master(self, token, server_game):
        """ Return True if given token is a master token for given game data.

            :param token: token
            :param server_game: game data
            :return: a boolean
            :type server_game: ServerGame
            :rtype: bool
        """
        return (self.users.has_token(token)
                and self.user_is_master(self.users.get_name(token), server_game))

    def token_is_omniscient(self, token, server_game):
        """ Return True if given token is omniscient for given game data.

            :param token: token
            :param server_game: game data
            :return: a boolean
            :type server_game: ServerGame
            :rtype: bool
        """
        return (self.users.has_token(token)
                and self.user_is_omniscient(self.users.get_name(token), server_game))

    def create_game_id(self):
        """ Create and return a game ID not already used by a game in server database. """
        game_id = base64.b64encode(os.urandom(12), b'-_').decode('utf-8')
        while self.has_game_id(game_id):
            game_id = base64.b64encode(os.urandom(12), b'-_').decode('utf-8')
        return game_id

    def remove_token(self, token):
        """ Disconnect given token from related user and loaded games. Stop related games if needed,
            e.g. if a game does not have anymore expected number of controlled powers.
        """
        self.users.disconnect_token(token)
        for server_game in self.games.values():  # type: ServerGame
            server_game.remove_token(token)
            self.stop_game_if_needed(server_game)
            self.save_game(server_game)
        self.save_data()

    def assert_token(self, token, connection_handler):
        """ Check if given token is associated to an user, check if token is still valid,
            and link token to given connection handler. If any step failed, raise an exception.

            :param token: token to check
            :param connection_handler: connection handler associated to this token
        """
        if not self.users.has_token(token):
            raise exceptions.TokenException()
        if self.users.token_is_alive(token):
            self.users.relaunch_token(token)
            self.save_data()
        else:
            # Logout on server side and raise exception (invalid token).
            LOGGER.error('Token too old %s', token)
            self.remove_token(token)
            raise exceptions.TokenException()
        self.users.attach_connection_handler(token, connection_handler)

    def assert_admin_token(self, token):
        """ Check if given token is an admin token. Raise an exception on error. """
        if not self.users.token_is_admin(token):
            raise exceptions.AdminTokenException()

    def assert_master_token(self, token, server_game):
        """ Check if given token is a master token for given game data. Raise an exception on error.

            :param token: token
            :param server_game: game data
            :type server_game: ServerGame
        """
        if not self.token_is_master(token, server_game):
            raise exceptions.GameMasterTokenException()

    def cannot_create_more_games(self):
        """ Return True if server can not accept new games. """
        return self.max_games and self.count_server_games() >= self.max_games

    def get_map(self, map_name):
        """ Return map power names for given map name. """
        return self.available_maps.get(map_name, None)

    def start_new_daide_server(self, game_id, port=None):
        """ Start a new DAIDE TCP server to handle DAIDE clients connections

            :param game_id: game id to pass to the DAIDE server
            :param port: the port to use. If None, an available random port will be used
        """
        if port in self.daide_servers:
            raise RuntimeError('Port already in used by a DAIDE server')

        for server in self.daide_servers.values():
            if server.game_id == game_id:
                return None

        while port is None or is_port_opened(port):
            port = randint(8000, 8999)

        # Create DAIDE TCP server
        daide_server = DaideServer(self, game_id)
        daide_server.listen(port)
        self.daide_servers[port] = daide_server
        LOGGER.info('DAIDE server running for game %s on port %d', game_id, port)
        return port

    def stop_daide_server(self, game_id):
        """ Stop one or all DAIDE TCP server

            :param game_id: game id of the DAIDE server. If None, all servers will be stopped
            :type game_id: str
        """
        for port in list(self.daide_servers.keys()):
            server = self.daide_servers[port]
            if game_id is None or server.game_id == game_id:
                server.stop()
                del self.daide_servers[port]

    def get_daide_port(self, game_id):
        """ Get the DAIDE port opened for a specific game_id

            :param game_id: game id of the DAIDE server.
        """
        for port, server in self.daide_servers.items():
            if server.game_id == game_id:
                return port
        return None
