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
""" Common utils symbols used in diplomacy network code. """
import base64
import binascii
import hashlib
import traceback
import os
import re
import sys
from datetime import datetime

import bcrypt

from diplomacy.utils.exceptions import CommonKeyException

# Datetime since timestamp 0.
EPOCH = datetime.utcfromtimestamp(0)

# Regex used for conversion from camel case to snake case.
REGEX_CONSECUTIVE_UPPER_CASES = re.compile('[A-Z]{2,}')
REGEX_LOWER_THEN_UPPER_CASES = re.compile('([a-z0-9])([A-Z])')
REGEX_UNDERSCORE_THEN_LETTER = re.compile('_([a-z])')
REGEX_START_BY_LOWERCASE = re.compile('^[a-z]')

def _sub_hash_password(password):
    """ Hash long password to allow bcrypt to handle password longer than 72 characters.
        Module private method.

        :param password: password to hash.
        :return: The hashed password.
        :rtype: str
    """
    # Bcrypt only handles passwords up to 72 characters. We use this hashing method as a work around.
    # Suggested in bcrypt PyPI page (2018/02/08 12:36 EST): https://pypi.python.org/pypi/bcrypt/3.1.0
    return base64.b64encode(hashlib.sha256(password.encode('utf-8')).digest())

def is_valid_password(password, hashed):
    """ Check if password matches hashed.

        :param password: password to check.
        :param hashed: a password hashed with method hash_password().
        :return: Indicates if the password matches the hash.
        :rtype: bool
    """
    return bcrypt.checkpw(_sub_hash_password(password), hashed.encode('utf-8'))

def hash_password(password):
    """ Hash password. Accepts password longer than 72 characters. Public method.

        :param password: The password to hash
        :return: The hashed password.
        :rtype: str
    """
    return bcrypt.hashpw(_sub_hash_password(password), bcrypt.gensalt(14)).decode('utf-8')

def generate_token(n_bytes=128):
    """ Generate a token with 2 * n_bytes characters (n_bytes bytes encoded in hexadecimal). """
    return binascii.hexlify(os.urandom(n_bytes)).decode('utf-8')

def is_dictionary(dict_to_check):
    """ Check if given variable is a dictionary-like object.

        :param dict_to_check: Dictionary to check.
        :return: Indicates if the object is a dictionary.
        :rtype: bool
    """
    return isinstance(dict_to_check, dict) or all(
        hasattr(dict_to_check, expected_attribute)
        for expected_attribute in (
            '__len__',
            '__contains__',
            '__bool__',
            '__iter__',
            '__getitem__',
            'keys',
            'values',
            'items',
        )
    )

def is_sequence(seq_to_check):
    """ Check if given variable is a sequence-like object.
        Note that strings and dictionary-like objects will not be considered as sequences.

        :param seq_to_check: Sequence-like object to check.
        :return: Indicates if the object is sequence-like.
        :rtype: bool
    """
    # Strings and dicts are not valid sequences.
    if isinstance(seq_to_check, str) or is_dictionary(seq_to_check):
        return False
    return hasattr(seq_to_check, '__iter__')

def camel_case_to_snake_case(name):
    """ Convert a string (expected to be in camel case) to snake case.

        :param name: string to convert.
        :return: snake case version of given name.
        :rtype: str
    """
    if name == '':
        return name
    separated_consecutive_uppers = REGEX_CONSECUTIVE_UPPER_CASES.sub(lambda m: '_'.join(c for c in m.group(0)), name)
    return REGEX_LOWER_THEN_UPPER_CASES.sub(r'\1_\2', separated_consecutive_uppers).lower()

def snake_case_to_upper_camel_case(name):
    """ Convert a string (expected to be in snake case) to camel case and convert first letter
        to upper case if it's in lowercase.

        :param name: string to convert.
        :return: camel case version of given name.
        :rtype: str
    """
    if name == '':
        return name
    first_lower_case_to_upper = REGEX_START_BY_LOWERCASE.sub(lambda m: m.group(0).upper(), name)
    return REGEX_UNDERSCORE_THEN_LETTER.sub(lambda m: m.group(1).upper(), first_lower_case_to_upper)

def assert_no_common_keys(dict1, dict2):
    """ Check that dictionaries does not share keys.

        :param dict1: dict
        :param dict2: dict
    """
    if len(dict1) < len(dict2):
        smallest_dict, biggest_dict = dict1, dict2
    else:
        smallest_dict, biggest_dict = dict2, dict1
    for key in smallest_dict:
        if key in biggest_dict:
            raise CommonKeyException(key)

def timestamp_microseconds():
    """ Return current timestamp with microsecond resolution.

        :rtype: int
    """
    delta = datetime.now() - EPOCH
    return (delta.days * 24 * 60 * 60 + delta.seconds) * 1000000 + delta.microseconds

def str_cmp_class(compare_function):
    """ Return a new class to be used as string comparator.

        Example:

        .. code-block:: python

            def my_cmp_func(a, b):
                # a and b are two strings to compare with a specific code.
                # Return -1 if a < b, 0 if a == b, 1 otherwise.

            my_class = str_cmp_class(my_cmp_func)
            wrapped_str_1 = my_class(str_to_compare_1)
            wrapped_str_2 = my_class(str_to_compare_2)
            my_list = [wrapped_str_1, wrapped_str_2]

            # my_list will be sorted according to my_cmp_func.
            my_list.sort()

        :param compare_function: a callable that takes 2 strings a and b, and compares
            it according to custom rules. This function should return:

            * -1 (or a negative value) if a < b
            * 0 if a == b
            * 1 (or a positive value) if a > b
        :return: a comparator class, instanciable with a string.
        :type compare_function: callable
    """

    class StringComparator:
        """ A comparable wrapper class around strings. """

        def __init__(self, value):
            """ Initialize comparator with a value. Expected a string value. """
            self.value = str(value)
            self.cmp_fn = compare_function

        def __str__(self):
            return self.value

        def __repr__(self):
            return repr(self.value)

        def __hash__(self):
            return hash(self.value)

        def __eq__(self, other):
            return self.cmp_fn(self.value, str(other)) == 0

        def __lt__(self, other):
            return self.cmp_fn(self.value, str(other)) < 0
    StringComparator.__name__ = 'StringComparator%s' % (id(compare_function))
    return StringComparator

def to_string(element):
    """ Convert element to a string and make sure string is wrapped in either simple quotes
        (if contains double quotes) or double quotes (if contains simple quotes).

        :param element: element to convert
        :return: string version of element
        :rtype: str
    """
    element = str(element)
    if '"' in element:
        return "'%s'" % element
    if "'" in element:
        return '"%s"' % element
    return element

class StringableCode:
    """ Represents a stringable version of a code (with an optional message) """
    def __init__(self, code, message=None):
        """ Build a StringableCode

            :param code: int - code
            :param message: Optional. human readable string message associated to the code
        """
        if isinstance(code, str) or message is None:
            message = code
            code = None

        if code is None:
            message_parts = message.split(':')
            if message_parts and message_parts[0].isdigit():
                code = int(message_parts[0])
                message = ':'.join(message_parts[1:])
            elif len(message_parts) == 1:
                message = message_parts[0]

        self._code = code
        self._message = message

    def __eq__(self, other):
        """ Define the equal """
        if isinstance(other, StringableCode):
            return self._code == other.code
        return self._message == str(other)

    def __hash__(self):
        """ Define the hash """
        return hash(self._message)

    def __mod__(self, values):
        """ Define the modulus. Apply the modulus on the message """
        return StringableCode(self._code, self._message % values)

    def __str__(self):
        """ Defines the str representation """
        return str(self.message)

    def __repr__(self):
        """ Define the string representation """
        return '{}:{}'.format(self._code, self._message)

    @property
    def code(self):
        """ Return the code of the result """
        return self._code

    @property
    def message(self):
        """ Return the message of the result """
        return self._message

    def format(self, *values):
        """ Format the message of the result """
        return StringableCode(self._code, self._message.format(*values))

class Tornado:
    """ Utilities for Tornado. """

    @staticmethod
    def stop_loop_on_callback_error(io_loop):
        """ Modify exception handler method of given IO loop so that IO loop stops and raises
            as soon as an exception is thrown from a callback.

            :param io_loop: IO loop
            :type io_loop: tornado.ioloop.IOLoop
        """

        def new_cb_exception_handler(callback):
            """ Callback exception handler used to replace IO loop default exception handler. """
            #pylint: disable=unused-argument
            _, exc_value, _ = sys.exc_info()
            io_loop.stop()
            traceback.print_tb(exc_value.__traceback__)
            print(type(exc_value).__name__)
            print(exc_value)
            exit(-1)

        io_loop.handle_callback_exception = new_cb_exception_handler
