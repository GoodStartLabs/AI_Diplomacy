#!/usr/bin/env python3
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
""" Small module script to quickly start a server with pretty log-printing.

    You can stop the server with keyboard interruption (Ctrl+C). Usage:

    .. code-block:: bash

        # run on port 8432.
        python -m diplomacy.server.run

        # run on given port.
        python -m diplomacy.server.run --port=<given port>

"""
import argparse
from diplomacy import Server
from diplomacy.utils import constants

if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(description='Run server.')
    PARSER.add_argument('--port', '-p', type=int, default=constants.DEFAULT_PORT,
                        help='run on the given port (default: %s)' % constants.DEFAULT_PORT)
    ARGS = PARSER.parse_args()

    try:
        Server().start(port=ARGS.port)
    except KeyboardInterrupt:
        print('Keyboard interruption.')
