#!/usr/bin/env python3
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
""" Run tests from diplomacy.tests.network.test_real_game to test games in a real environment.
    Each test run a game and checks game messages and phases against an expected game data file.
    Current tested gama data files are JSON files located into folder diplomacy/tests/network:

    - 1.json
    - 2.json
    - 3.json

    Need a local diplomacy server running. You must specify
    this server port using parameter ``--port=<server_port>``.

    To run all tests: ::

        python -m diplomacy.tests.network.run_real_game --port=<server_port>

    To run a specific test (e.g. 2.json, or 2.json and 1.json): ::

        python -m diplomacy.tests.network.run_real_game --cases=2 --port=<server_port>
        python -m diplomacy.tests.network.run_real_game --cases=1,2 --port=<server_port>

    For help: ::

        python -m diplomacy.tests.network.run_real_game --help

"""
import argparse
from tornado import gen
from tornado.ioloop import IOLoop

from diplomacy.tests.network import test_real_game

def launch_case(case_name, port, io_loop):
    """ Launch a game case. """
    case_data = test_real_game.CaseData(case_name, port=port)
    case_data.io_loop = io_loop
    return test_real_game.main(case_data)

def main():
    """ Main function for this module. Load and run tests.
        Each test run a game and checks game messages and phases against an expected game data file.
        Current tested gama data files are JSON files located into folder diplomacy/tests/network.
    """
    parser = argparse.ArgumentParser(description='Run test cases against an external server to connect.')
    parser.add_argument('--port', type=int, required=True,
                        help='run on the given port (required)')
    parser.add_argument('--cases', action='append',
                        help="Run given cases. "
                             "Each case <C> must match a test case file <C>.json located in diplomacy.tests.network. "
                             "If not provided, all available cases are run.")
    args = parser.parse_args()
    io_loop = IOLoop()
    io_loop.make_current()

    @gen.coroutine
    def run():
        """ Run all tests consecutively in one call. """
        tests = set(args.cases) if args.cases else {'1', '2', '3'}
        for test_case in list(sorted(tests)):
            yield launch_case('%s.json' % test_case, args.port, io_loop)

    io_loop.run_sync(run)


if __name__ == '__main__':
    main()
