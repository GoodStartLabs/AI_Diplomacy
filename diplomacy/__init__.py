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
""" Module diplomacy, represent strategy game Diplomacy. """
import logging
import os
import coloredlogs
from .engine.map import Map
from .engine.power import Power
from .engine.game import Game
from .engine.message import Message
from .client.connection import Connection, connect
from .server.server import Server
from .utils.game_phase_data import GamePhaseData

# Defining root logger
ROOT = logging.getLogger('diplomacy')
ROOT.setLevel(logging.DEBUG)
ROOT.propagate = False

STREAM_HANDLER = logging.StreamHandler()
STREAM_HANDLER.setLevel(logging.DEBUG)
COLORED_FORMATTER = coloredlogs.ColoredFormatter(fmt='%(asctime)s %(name)s[%(process)d] %(levelname)s %(message)s')
STREAM_HANDLER.setFormatter(COLORED_FORMATTER)
ROOT.addHandler(STREAM_HANDLER)

if 'DIPLOMACY_LOG_FILE' in os.environ:
    LOG_FILE_NAME = os.environ['DIPLOMACY_LOG_FILE']
    ROOT.info('Logging into file: %s', LOG_FILE_NAME)
    FILE_HANDLER = logging.FileHandler(LOG_FILE_NAME)
    FILE_HANDLER.setLevel(logging.DEBUG)
    LOG_FILE_FORMATTER = logging.Formatter(fmt='%(asctime)s %(name)s[%(process)d] %(levelname)s %(message)s')
    FILE_HANDLER.setFormatter(LOG_FILE_FORMATTER)
    ROOT.addHandler(FILE_HANDLER)
