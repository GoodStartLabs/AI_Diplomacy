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
""" Results

    - Contains the results labels and code used by the engine
"""
from diplomacy.utils.common import StringableCode

# Constants
ORDER_RESULT_OFFSET = 10000

class OrderResult(StringableCode):
    """ Represents an order result """
    def __init__(self, code, message):
        """ Build a Order Result

            :param code: int code of the order result
            :param message: human readable string message associated to the order result
        """
        super(OrderResult, self).__init__(code, message)

OK = OrderResult(0, '')
"""Order result OK, printed as ``''``"""

NO_CONVOY = OrderResult(ORDER_RESULT_OFFSET + 1, 'no convoy')
"""Order result NO_CONVOY, printed as ``'no convoy'``"""

BOUNCE = OrderResult(ORDER_RESULT_OFFSET + 2, 'bounce')
"""Order result BOUNCE, printed as ``'bounce'``"""

VOID = OrderResult(ORDER_RESULT_OFFSET + 3, 'void')
"""Order result VOID, printed as ``'void'``"""

CUT = OrderResult(ORDER_RESULT_OFFSET + 4, 'cut')
"""Order result CUT, printed as ``'cut'``"""

DISLODGED = OrderResult(ORDER_RESULT_OFFSET + 5, 'dislodged')
"""Order result DISLODGED, printed as ``'dislodged'``"""

DISRUPTED = OrderResult(ORDER_RESULT_OFFSET + 6, 'disrupted')
"""Order result DISRUPTED, printed as ``'disrupted'``"""

DISBAND = OrderResult(ORDER_RESULT_OFFSET + 7, 'disband')
"""Order result DISBAND, printed as ``'disband'``"""

MAYBE = OrderResult(ORDER_RESULT_OFFSET + 8, 'maybe')
"""Order result MAYBE, printed as ``'maybe'``"""
