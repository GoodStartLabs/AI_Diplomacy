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
""" Test for diplomacy network code utils. """
import ujson as json

from diplomacy.utils import common, exceptions

def assert_raises(callback, expected_exceptions):
    """ Checks that given callback raises given exceptions. """

    try:
        callback()
    except expected_exceptions:
        pass
    else:
        raise AssertionError('Should fail %s %s' % (callback, str(expected_exceptions)))

def assert_equals(expected, computed):
    """ Checks that expect == computed. """

    if expected != computed:
        raise AssertionError('\nExpected:\n=========\n%s\n\nComputed:\n=========\n%s\n' % (expected, computed))

def test_hash_password():
    """ Test passwords hashing. Note: slower than the other tests. """

    password1 = '123456789'
    password2 = 'abcdef'
    password_unicode = 'しろいねこをみた。 白い猫を見た。'
    for password in (password1, password2, password_unicode):
        hashed_password = common.hash_password(password)
        json_hashed_password = json.dumps(common.hash_password(password))
        hashed_password_from_json = json.loads(json_hashed_password)
        # It seems hashed passwords are not necessarily the same for 2 different calls to hash function.
        assert common.is_valid_password(password, hashed_password), (password, hashed_password)
        assert common.is_valid_password(password, hashed_password_from_json), (password, hashed_password_from_json)

def test_generate_token():
    """ Test token generation. """

    for n_bytes in (128, 344):
        token = common.generate_token(n_bytes)
        assert isinstance(token, str) and len(token) == 2 * n_bytes

def test_is_sequence():
    """ Test sequence type checking function. """

    assert common.is_sequence((1, 2, 3))
    assert common.is_sequence([1, 2, 3])
    assert common.is_sequence({1, 2, 3})
    assert common.is_sequence(())
    assert common.is_sequence([])
    assert common.is_sequence(set())
    assert not common.is_sequence('i am a string')
    assert not common.is_sequence({})
    assert not common.is_sequence(1)
    assert not common.is_sequence(False)
    assert not common.is_sequence(-2.5)

def test_is_dictionary():
    """ Test dictionary type checking function. """

    assert common.is_dictionary({'a': 1, 'b': 2})
    assert not common.is_dictionary((1, 2, 3))
    assert not common.is_dictionary([1, 2, 3])
    assert not common.is_dictionary({1, 2, 3})

    assert not common.is_dictionary(())
    assert not common.is_dictionary([])
    assert not common.is_dictionary(set())

    assert not common.is_dictionary('i am a string')

def test_camel_to_snake_case():
    """ Test conversion from camel case to snake case. """

    for camel, expected_snake in [
            ('a', 'a'),
            ('A', 'a'),
            ('AA', 'a_a'),
            ('AbCdEEf', 'ab_cd_e_ef'),
            ('Aa', 'aa'),
            ('OnGameDone', 'on_game_done'),
            ('AbstractSuperClass', 'abstract_super_class'),
            ('ABCDEFghikKLm', 'a_b_c_d_e_fghik_k_lm'),
            ('is_a_thing', 'is_a_thing'),
            ('A_a_Aa__', 'a_a_aa__'),
            ('Horrible_SuperClass_nameWith_mixedSyntax', 'horrible_super_class_name_with_mixed_syntax'),
    ]:
        computed_snake = common.camel_case_to_snake_case(camel)
        assert computed_snake == expected_snake, ('camel : expected : computed:', camel, expected_snake, computed_snake)

def test_snake_to_camel_case():
    """ Test conversion from snake case to camel upper case. """

    for expected_camel, snake in [
            ('A', 'a'),
            ('AA', 'a_a'),
            ('AbCdEEf', 'ab_cd_e_ef'),
            ('Aa', 'aa'),
            ('OnGameDone', 'on_game_done'),
            ('AbstractSuperClass', 'abstract_super_class'),
            ('ABCDEFghikKLm', 'a_b_c_d_e_fghik_k_lm'),
            ('IsAThing', 'is_a_thing'),
            ('AAAa__', 'a_a_aa__'),
            ('_AnHorrible_ClassName', '__an_horrible__class_name'),
    ]:
        computed_camel = common.snake_case_to_upper_camel_case(snake)
        assert computed_camel == expected_camel, ('snake : expected : computed:', snake, expected_camel, computed_camel)

def test_assert_no_common_keys():
    """ Test dictionary disjunction checking function. """

    dct1 = {'a': 1, 'b': 2, 'c': 3}
    dct2 = {'a': 1, 'e': 2, 'd': 3}
    dct3 = {'m': 1, 'e': 2, 'f': 3}
    common.assert_no_common_keys(dct1, dct3)
    assert_raises(lambda: common.assert_no_common_keys(dct1, dct2), exceptions.CommonKeyException)
    assert_raises(lambda: common.assert_no_common_keys(dct2, dct3), exceptions.CommonKeyException)

def test_timestamp():
    """ Test timestamp generation. """

    timestamp1 = common.timestamp_microseconds()
    timestamp2 = common.timestamp_microseconds()
    timestamp3 = common.timestamp_microseconds()
    assert isinstance(timestamp1, int)
    assert isinstance(timestamp2, int)
    assert isinstance(timestamp3, int)
    assert timestamp1 > 1e6
    assert timestamp2 > 1e6
    assert timestamp3 > 1e6
    assert timestamp1 <= timestamp2 <= timestamp3, (timestamp1, timestamp2, timestamp3)
