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
# pylint: disable=anomalous-backslash-in-string
""" Helper class to compute intersection of a line (OM) with a side of an equilateral triangle,
    with O the barycenter of the equilateral triangle and M a point outside the triangle.::

                 A
               /  |     M
             /  O |
        C  /______|  B

        A = top, B = right, C = left
        O = center of triangle
        M = point outside of triangle

"""
class EquilateralTriangle:
    """ Helper class that represent an equilateral triangle.
        Used to compute intersection of a line with a side of convoy symbol, which is an equilateral triangle.
    """
    __slots__ = ('x_a', 'y_a', 'x_b', 'y_b', 'x_c', 'y_c', 'x_o', 'y_o', 'height',
                 'line_ab_a', 'line_ab_b', 'line_ac_a', 'line_ac_b')

    def __init__(self, x_top, y_top, x_right, y_right, x_left, y_left):
        """ Constructor """
        assert y_left == y_right > y_top
        assert x_left < x_top < x_right
        self.x_a = x_top
        self.y_a = y_top
        self.x_b = x_right
        self.y_b = y_right
        self.x_c = x_left
        self.y_c = y_left
        self.height = self.y_b - self.y_a
        self.x_o = self.x_a
        self.y_o = self.y_a + 2 * self.height / 3
        self.line_ab_a = (self.y_b - self.y_a) / (self.x_b - self.x_a)
        self.line_ab_b = self.y_b - self.x_b * self.line_ab_a
        self.line_ac_a = (self.y_c - self.y_a) / (self.x_c - self.x_a)
        self.line_ac_b = self.y_c - self.x_c * self.line_ac_a

    def __line_om(self, x_m, y_m):
        """ Returns the slope and the intersect of the line between O and M

            :return: a, b - respectively the slope and the intercept of the line OM
        """
        # pylint:disable=invalid-name
        a = (y_m - self.y_o) / (x_m - self.x_o)
        b = y_m - a * x_m
        return a, b

    def _intersection_with_ab(self, x_m, y_m):
        """ Return coordinates of intersection of line (OM) with line (AB).

            :param x_m: x coordinate of M
            :param y_m: y coordinate of M
            :return: coordinates (x, y) of intersection, or (None, None) if either
                (OM) and (AB) don't intersect, or intersection point is not in segment AB.
        """
        # pylint:disable=invalid-name
        a, b = self.line_ab_a, self.line_ab_b
        if x_m == self.x_o:
            # (OM) is a vertical line
            x = x_m
        else:
            u, v = self.__line_om(x_m, y_m)
            if a == u:
                # (OM) and (AB) are parallel. No intersection.
                return None, None
            x = (v - b) / (a - u)
        y = a * x + b
        if self.x_a <= x <= self.x_b and self.y_a <= y <= self.y_b:
            return x, y
        return None, None

    def _intersection_with_ac(self, x_m, y_m):
        """ Return coordinates of intersection of line (OM) with line (AC).

            :param x_m: x coordinate of M
            :param y_m: y coordinate of M
            :return: coordinates (x, y) of intersection, or (None, None) if either
                (OM) and (AC) don't intersect, or intersection point is not in segment AC.
        """
        # pylint:disable=invalid-name
        a, b = self.line_ac_a, self.line_ac_b
        if x_m == self.x_o:
            x = x_m
        else:
            u, v = self.__line_om(x_m, y_m)
            if a == u:
                return None, None
            x = (v - b) / (a - u)
        y = a * x + b
        if self.x_c <= x <= self.x_a and self.y_a <= y <= self.y_c:
            return x, y
        return None, None

    def _intersection_with_bc(self, x_m, y_m):
        """ Return coordinates of intersection of line (OM) with line (BC).
            NB: (BC) is an horizontal line.

            :param x_m: x coordinate of M
            :param y_m: y coordinate of M
            :return: coordinates (x, y) of intersection, or (None, None) if either
                (OM) and (BC) don't intersect, or intersection point is not in segment BC.
        """
        # pylint:disable=invalid-name
        y = self.y_c
        if x_m == self.x_o:
            x = x_m
        else:
            a, b = self.__line_om(x_m, y_m)
            if a == 0:
                return None, None
            x = (y - b) / a
        if self.x_c <= x <= self.x_a:
            return x, y
        return None, None

    def intersection(self, x_m, y_m):
        """ Return coordinates of the intersection of (OM) with equilateral triangle,
            with M the point with coordinates (x_m, y_m). Only the intersection with
            the side of triangle near M is considered.

            :param x_m: x coordinate of M
            :param y_m: y coordinate of M
            :return: a couple (x, y) of floating values.
        """
        # pylint:disable=invalid-name
        if self.x_o == x_m and self.y_o == y_m:
            return x_m, y_m

        if self.x_o == x_m:
            if y_m < self.y_o:
                return x_m, self.y_a
            # Otherwise, vertical line intersects BC
            return x_m, self.y_c

        if self.y_o == y_m:
            if x_m < self.x_o:
                # horizontal line intersects AC
                a, b = self.line_ac_a, self.line_ac_b
            else:
                # horizontal line intersects AB
                a, b = self.line_ab_a, self.line_ab_b
            x = (y_m - b) / a
            return x, y_m

        # Otherwise, get nearest point in intersections with AB, AC, BC
        p1_x, p1_y = self._intersection_with_ab(x_m, y_m)
        p2_x, p2_y = self._intersection_with_ac(x_m, y_m)
        p3_x, p3_y = self._intersection_with_bc(x_m, y_m)
        distances = []
        if p1_x is not None:
            distance_1 = ((p1_x - x_m) ** 2 + (p1_y - y_m) ** 2) ** 0.5
            distances.append((distance_1, p1_x, p1_y))
        if p2_x is not None:
            distance_2 = ((p2_x - x_m) ** 2 + (p2_y - y_m) ** 2) ** 0.5
            distances.append((distance_2, p2_x, p2_y))
        if p3_x is not None:
            distance_3 = ((p3_x - x_m) ** 2 + (p3_y - y_m) ** 2) ** 0.5
            distances.append((distance_3, p3_x, p3_y))

        assert distances
        distances.sort()
        return distances[0][1:]
