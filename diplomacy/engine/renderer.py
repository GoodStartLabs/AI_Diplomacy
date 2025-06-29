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
# -*- coding: utf-8 -*-
""" Renderer

    - Contains the renderer object which is responsible for rendering a game state to svg
"""
import os
from xml.dom import minidom
from typing import Tuple
from diplomacy import settings
from diplomacy.utils.equilateral_triangle import EquilateralTriangle

# Constants
LAYER_ORDER = 'OrderLayer'
LAYER_UNIT = 'UnitLayer'
LAYER_DISL = 'DislodgedUnitLayer'
ARMY = 'Army'
FLEET = 'Fleet'

def _attr(node_element, attr_name):
    """ Shorthand method to retrieve an XML attribute """
    return node_element.attributes[attr_name].value

class Renderer:
    """ Renderer object responsible for rendering a game state to svg """

    def __init__(self, game, svg_path=None):
        """ Constructor

            :param game: The instantiated game object to render
            :param svg_path: Optional. Can be set to the full path of a custom SVG to use for rendering the map.
            :type game: diplomacy.Game
            :type svg_path: str, optional
        """
        self.game = game
        self.metadata = {}
        self.xml_map = None

        # If no SVG path provided, we default to the one in the maps folder
        if not svg_path:
            for file_name in [self.game.map.name + '.svg', self.game.map.root_map + '.svg']:
                svg_path = os.path.join(settings.PACKAGE_DIR, 'maps', 'svg', file_name)
                if os.path.exists(svg_path):
                    break

        # Loading XML
        if os.path.exists(svg_path):
            self.xml_map = minidom.parse(svg_path).toxml()
        self._load_metadata()

    def render(self, incl_orders=True, incl_abbrev=False, output_format='svg', output_path=None):
        """ Renders the current game and returns the XML representation

            :param incl_orders:  Optional. Flag to indicate we also want to render orders.
            :param incl_abbrev: Optional. Flag to indicate we also want to display the provinces abbreviations.
            :param output_format: The desired output format. Valid values are: 'svg'
            :param output_path: Optional. The full path where to save the rendering on disk.
            :type incl_orders: bool, optional
            :type incl_abbrev: bool, optional
            :type output_format: str, optional
            :type output_path: str | None, optional
            :return: The rendered image in the specified format.
        """
        # pylint: disable=too-many-branches
        if output_format not in ['svg']:
            raise ValueError('Only "svg" format is current supported.')
        if not self.game or not self.game.map or not self.xml_map:
            return None

        # Parsing XML
        xml_map = minidom.parseString(self.xml_map)

        # Setting phase and note
        nb_centers = [(power.name[:3], len(power.centers))
                      for power in self.game.powers.values()
                      if not power.is_eliminated()]
        nb_centers = sorted(nb_centers, key=lambda key: key[1], reverse=True)
        nb_centers_per_power = ' '.join(['{}: {}'.format(name, centers) for name, centers in nb_centers])
        xml_map = self._set_current_phase(xml_map, self.game.get_current_phase())
        xml_map = self._set_note(xml_map, nb_centers_per_power, self.game.note)

        # Adding units and influence
        for power in self.game.powers.values():
            for unit in power.units:
                xml_map = self._add_unit(xml_map, unit, power.name, is_dislodged=False)
            for unit in power.retreats:
                xml_map = self._add_unit(xml_map, unit, power.name, is_dislodged=True)
            for center in power.centers:
                xml_map = self._set_influence(xml_map, center, power.name, has_supply_center=True)
            for loc in power.influence:
                xml_map = self._set_influence(xml_map, loc, power.name, has_supply_center=False)

            # Orders
            if incl_orders:

                # Regular orders (Normalized)
                # A PAR H
                # A PAR - BUR [VIA]
                # A PAR S BUR
                # A PAR S F BRE - PIC
                # F BRE C A PAR - LON
                for order_key in power.orders:

                    # No_check order (Order, Invalid, Reorder)
                    # Otherwise regular order (unit is key, order without unit is value)
                    if order_key[0] in 'RIO':
                        order = power.orders[order_key]
                    else:
                        order = '{} {}'.format(order_key, power.orders[order_key])

                    # Normalizing and splitting in tokens
                    tokens = self._norm_order(order)
                    unit_loc = tokens[1]

                    # Parsing based on order type
                    if not tokens or len(tokens) < 3:
                        continue
                    elif tokens[2] == 'H':
                        xml_map = self._issue_hold_order(xml_map, unit_loc, power.name)
                    elif tokens[2] == '-':
                        dest_loc = tokens[-1] if tokens[-1] != 'VIA' else tokens[-2]
                        xml_map = self._issue_move_order(xml_map, unit_loc, dest_loc, power.name)
                    elif tokens[2] == 'S':
                        dest_loc = tokens[-1]
                        if '-' in tokens:
                            src_loc = tokens[4] if tokens[3] == 'A' or tokens[3] == 'F' else tokens[3]
                            xml_map = self._issue_support_move_order(xml_map, unit_loc, src_loc, dest_loc, power.name)
                        else:
                            xml_map = self._issue_support_hold_order(xml_map, unit_loc, dest_loc, power.name)
                    elif tokens[2] == 'C':
                        src_loc = tokens[4] if tokens[3] == 'A' or tokens[3] == 'F' else tokens[3]
                        dest_loc = tokens[-1]
                        if src_loc != dest_loc and '-' in tokens:
                            xml_map = self._issue_convoy_order(xml_map, unit_loc, src_loc, dest_loc, power.name)
                    else:
                        raise RuntimeError('Unknown order: {}'.format(' '.join(tokens)))

                # Adjustment orders
                # VOID xxx
                # A PAR B
                # A PAR D
                # A PAR R BUR
                # WAIVE
                for order in power.adjust:
                    tokens = order.split()
                    if not tokens or tokens[0] == 'VOID' or tokens[-1] == 'WAIVE':
                        continue
                    elif tokens[-1] == 'B':
                        if len(tokens) < 3:
                            continue
                        xml_map = self._issue_build_order(xml_map, tokens[0], tokens[1], power.name)
                    elif tokens[-1] == 'D':
                        xml_map = self._issue_disband_order(xml_map, tokens[1])
                    elif tokens[-2] == 'R':
                        src_loc = tokens[1] if tokens[0] == 'A' or tokens[0] == 'F' else tokens[0]
                        dest_loc = tokens[-1]
                        xml_map = self._issue_move_order(xml_map, src_loc, dest_loc, power.name)
                    else:
                        raise RuntimeError('Unknown order: {}'.format(order))

        # Removing abbrev and mouse layer
        svg_node = xml_map.getElementsByTagName('svg')[0]
        for child_node in svg_node.childNodes:
            if child_node.nodeName != 'g':
                continue
            if _attr(child_node, 'id') == 'BriefLabelLayer' and not incl_abbrev:
                svg_node.removeChild(child_node)
            elif _attr(child_node, 'id') == 'MouseLayer':
                svg_node.removeChild(child_node)

        # Rendering
        rendered_image = xml_map.toxml()

        # Saving to disk
        if output_path:
            with open(output_path, 'w') as output_file:
                output_file.write(rendered_image)

        # Returning
        return rendered_image

    def _load_metadata(self):
        """ Loads meta-data embedded in the XML map and clears unused nodes """
        if not self.xml_map:
            return
        xml_map = minidom.parseString(self.xml_map)

        # Data
        self.metadata = {
            'color': {},
            'symbol_size': {},
            'orders': {},
            'coord': {}
        }

        # Order drawings
        for order_drawing in xml_map.getElementsByTagName('jdipNS:ORDERDRAWING'):
            for child_node in order_drawing.childNodes:

                # Power Colors
                if child_node.nodeName == 'jdipNS:POWERCOLORS':
                    for power_color in child_node.childNodes:
                        if power_color.nodeName == 'jdipNS:POWERCOLOR':
                            self.metadata['color'][_attr(power_color, 'power').upper()] = _attr(power_color, 'color')

                # Symbol size
                elif child_node.nodeName == 'jdipNS:SYMBOLSIZE':
                    self.metadata['symbol_size'][_attr(child_node, 'name')] = (_attr(child_node, 'height'),
                                                                               _attr(child_node, 'width'))

        # Object coordinates
        for province_data in xml_map.getElementsByTagName('jdipNS:PROVINCE_DATA'):
            for child_node in province_data.childNodes:

                # Province
                if child_node.nodeName == 'jdipNS:PROVINCE':
                    province = _attr(child_node, 'name').upper().replace('-', '/')
                    self.metadata['coord'][province] = {}

                    for coord_node in child_node.childNodes:
                        if coord_node.nodeName == 'jdipNS:UNIT':
                            self.metadata['coord'][province]['unit'] = (_attr(coord_node, 'x'), _attr(coord_node, 'y'))
                        elif coord_node.nodeName == 'jdipNS:DISLODGED_UNIT':
                            self.metadata['coord'][province]['disl'] = (_attr(coord_node, 'x'), _attr(coord_node, 'y'))

        # Deleting
        svg_node = xml_map.getElementsByTagName('svg')[0]
        svg_node.removeChild(xml_map.getElementsByTagName('jdipNS:DISPLAY')[0])
        svg_node.removeChild(xml_map.getElementsByTagName('jdipNS:ORDERDRAWING')[0])
        svg_node.removeChild(xml_map.getElementsByTagName('jdipNS:PROVINCE_DATA')[0])
        self.xml_map = xml_map.toxml()

    def _norm_order(self, order):
        """ Normalizes the order format and split it into tokens
            This is only used for **movement** orders (to make sure NO_CHECK games used the correct format)

            Formats: ::

                A PAR H
                A PAR - BUR [VIA]
                A PAR S BUR
                A PAR S F BRE - PIC
                F BRE C A PAR - LON

            :param order: The unformatted order (e.g. 'Paris - Burgundy')
            :return: The tokens of the formatted order (e.g. ['A', 'PAR', '-', 'BUR'])
        """
        return self.game._add_unit_types(self.game._expand_order(order.split()))    # pylint: disable=protected-access

    def _add_unit(self, xml_map, unit, power_name, is_dislodged):
        """ Adds a unit to the map

            :param xml_map: The xml map being generated
            :param unit: The unit to add (e.g. 'A PAR')
            :param power_name: The name of the power owning the unit (e.g. 'FRANCE')
            :param is_dislodged: Boolean. Indicates if the unit is dislodged
            :return: Nothing
        """
        unit_type, loc = unit.split()
        symbol = FLEET if unit_type == 'F' else ARMY
        loc_x = self.metadata['coord'][loc][('unit', 'disl')[is_dislodged]][0]
        loc_y = self.metadata['coord'][loc][('unit', 'disl')[is_dislodged]][1]
        node = xml_map.createElement('use')
        node.setAttribute('id', '%sunit_%s' % ('dislodged_' if is_dislodged else '', loc))
        node.setAttribute('x', loc_x)
        node.setAttribute('y', loc_y)
        node.setAttribute('height', self.metadata['symbol_size'][symbol][0])
        node.setAttribute('width', self.metadata['symbol_size'][symbol][1])
        node.setAttribute('xlink:href', '#{}{}'.format(('', 'Dislodged')[is_dislodged], symbol))
        node.setAttribute('class', 'unit{}'.format(power_name.lower()))

        # Inserting
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' \
                    and _attr(child_node, 'id') == ['UnitLayer', 'DislodgedUnitLayer'][is_dislodged]:
                child_node.appendChild(node)
                break
        return xml_map

    def _set_influence(self, xml_map, loc, power_name, has_supply_center=False):
        """ Sets the influence on the map

            :param xml_map: The xml map being generated
            :param loc: The province being influenced (e.g. 'PAR')
            :param power_name: The name of the power influencing the province
            :param has_supply_center: Boolean flag to acknowledge we are modifying a loc with a SC
            :return: Nothing
        """
        loc = loc.upper()[:3]
        if loc in self.game.map.scs and not has_supply_center:
            return xml_map
        if self.game.map.area_type(loc) == 'WATER':
            return xml_map

        class_name = power_name.lower() if power_name else 'nopower'

        # Inserting
        map_layer = None
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' and _attr(child_node, 'id') == 'MapLayer':
                map_layer = child_node
                break

        if map_layer:
            for map_node in map_layer.childNodes:
                if (map_node.nodeName in ('g', 'path', 'polygon')
                        and map_node.getAttribute('id') == '_{}'.format(loc.lower())):

                    # Province is a polygon - Setting influence directly
                    if map_node.nodeName in ('path', 'polygon'):
                        map_node.setAttribute('class', class_name)
                        return xml_map

                    # Otherwise, map node is a 'g' node.
                    node_edited = False
                    for sub_node in map_node.childNodes:
                        if sub_node.nodeName in ('path', 'polygon') and sub_node.getAttribute('class') != 'water':
                            node_edited = True
                            sub_node.setAttribute('class', class_name)
                    if node_edited:
                        return xml_map

        # Returning
        return xml_map

    @staticmethod
    def _set_current_phase(xml_map, current_phase):
        """ Sets the phase text at the bottom right of the the map

            :param xml_map: The xml map being generated
            :param current_phase: The current phase (e.g. 'S1901M)
            :return: Nothing
        """
        current_phase = 'FINAL' if current_phase[0] == '?' or current_phase == 'COMPLETED' else current_phase
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'text' and _attr(child_node, 'id') == 'CurrentPhase':
                child_node.childNodes[0].nodeValue = current_phase
                return xml_map
        return xml_map

    @staticmethod
    def _set_note(xml_map, note_1, note_2):
        """ Sets a note at the top left of the map

            :param xml_map: The xml map being generated
            :param note_1: The text to display on the first line
            :param note_2: The text to display on the second line
            :return: Nothing
        """
        note_1 = note_1 or ' '
        note_2 = note_2 or ' '
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'text' and _attr(child_node, 'id') == 'CurrentNote':
                child_node.childNodes[0].nodeValue = note_1
            if child_node.nodeName == 'text' and _attr(child_node, 'id') == 'CurrentNote2':
                child_node.childNodes[0].nodeValue = note_2
        return xml_map

    def _issue_hold_order(self, xml_map, loc, power_name):
        """ Adds a hold order to the map

            :param xml_map: The xml map being generated
            :param loc: The province where the unit is holding (e.g. 'PAR')
            :param power_name: The name of the power owning the unit
            :return: Nothing
        """
        # Symbols
        symbol = 'HoldUnit'
        loc_x, loc_y = self._center_symbol_around_unit(loc, False, symbol)

        # Creating nodes
        g_node = xml_map.createElement('g')
        g_node.setAttribute('stroke', self.metadata['color'][power_name])
        symbol_node = xml_map.createElement('use')
        symbol_node.setAttribute('x', loc_x)
        symbol_node.setAttribute('y', loc_y)
        symbol_node.setAttribute('height', self.metadata['symbol_size'][symbol][0])
        symbol_node.setAttribute('width', self.metadata['symbol_size'][symbol][1])
        symbol_node.setAttribute('xlink:href', '#{}'.format(symbol))

        # Inserting
        g_node.appendChild(symbol_node)
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' and _attr(child_node, 'id') == 'OrderLayer':
                for layer_node in child_node.childNodes:
                    if layer_node.nodeName == 'g' and _attr(layer_node, 'id') == 'Layer1':
                        layer_node.appendChild(g_node)
                        return xml_map

        # Returning
        return xml_map

    def _issue_support_hold_order(self, xml_map, loc, dest_loc, power_name):
        """ Issues a support hold order

            :param xml_map: The xml map being generated
            :param loc: The location of the unit sending support (e.g. 'BER')
            :param dest_loc: The location where the unit is holding from (e.g. 'PAR')
            :param power_name: The power name issuing the move order
            :return: Nothing
        """
        # Symbols
        symbol = 'SupportHoldUnit'
        symbol_loc_x, symbol_loc_y = self._center_symbol_around_unit(dest_loc, False, symbol)
        symbol_node = xml_map.createElement('use')
        symbol_node.setAttribute('x', symbol_loc_x)
        symbol_node.setAttribute('y', symbol_loc_y)
        symbol_node.setAttribute('height', self.metadata['symbol_size'][symbol][0])
        symbol_node.setAttribute('width', self.metadata['symbol_size'][symbol][1])
        symbol_node.setAttribute('xlink:href', '#{}'.format(symbol))

        loc_x, loc_y = self._get_unit_center(loc, False)
        dest_loc_x, dest_loc_y = self._get_unit_center(dest_loc, False)

        # Adjusting destination
        delta_x = dest_loc_x - loc_x
        delta_y = dest_loc_y - loc_y
        vector_length = (delta_x ** 2 + delta_y ** 2) ** 0.5
        delta_dec = float(self.metadata['symbol_size'][symbol][1]) / 2
        dest_loc_x = round(loc_x + (vector_length - delta_dec) / vector_length * delta_x, 2)
        dest_loc_y = round(loc_y + (vector_length - delta_dec) / vector_length * delta_y, 2)

        # Creating nodes
        g_node = xml_map.createElement('g')
        g_node.setAttribute('stroke', self.metadata['color'][power_name])

        shadow_line = xml_map.createElement('line')
        shadow_line.setAttribute('x1', str(loc_x))
        shadow_line.setAttribute('y1', str(loc_y))
        shadow_line.setAttribute('x2', str(dest_loc_x))
        shadow_line.setAttribute('y2', str(dest_loc_y))
        shadow_line.setAttribute('class', 'shadowdash')

        support_line = xml_map.createElement('line')
        support_line.setAttribute('x1', str(loc_x))
        support_line.setAttribute('y1', str(loc_y))
        support_line.setAttribute('x2', str(dest_loc_x))
        support_line.setAttribute('y2', str(dest_loc_y))
        support_line.setAttribute('class', 'supportorder')

        # Inserting
        g_node.appendChild(shadow_line)
        g_node.appendChild(support_line)
        g_node.appendChild(symbol_node)

        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' and _attr(child_node, 'id') == 'OrderLayer':
                for layer_node in child_node.childNodes:
                    if layer_node.nodeName == 'g' and _attr(layer_node, 'id') == 'Layer2':
                        layer_node.appendChild(g_node)
                        return xml_map

        # Returning
        return xml_map

    def _issue_move_order(self, xml_map, src_loc, dest_loc, power_name):
        """ Issues a move order

            :param xml_map: The xml map being generated
            :param src_loc: The location where the unit is moving from (e.g. 'PAR')
            :param dest_loc: The location where the unit is moving to (e.g. 'MAR')
            :param power_name: The power name issuing the move order
            :return: Nothing
        """
        is_dislodged = self.game.get_current_phase()[-1] == 'R'
        src_loc_x, src_loc_y = self._get_unit_center(src_loc, is_dislodged)
        dest_loc_x, dest_loc_y = self._get_unit_center(dest_loc, is_dislodged)

        # Adjusting destination
        delta_x = dest_loc_x - src_loc_x
        delta_y = dest_loc_y - src_loc_y
        vector_length = (delta_x ** 2 + delta_y ** 2) ** 0.5
        delta_dec = float(self.metadata['symbol_size'][ARMY][1]) / 2 + 2 * self._colored_stroke_width()
        dest_loc_x = str(round(src_loc_x + (vector_length - delta_dec) / vector_length * delta_x, 2))
        dest_loc_y = str(round(src_loc_y + (vector_length - delta_dec) / vector_length * delta_y, 2))

        src_loc_x = str(src_loc_x)
        src_loc_y = str(src_loc_y)
        dest_loc_x = str(dest_loc_x)
        dest_loc_y = str(dest_loc_y)

        # Creating nodes
        g_node = xml_map.createElement('g')

        line_with_shadow = xml_map.createElement('line')
        line_with_shadow.setAttribute('x1', src_loc_x)
        line_with_shadow.setAttribute('y1', src_loc_y)
        line_with_shadow.setAttribute('x2', dest_loc_x)
        line_with_shadow.setAttribute('y2', dest_loc_y)
        line_with_shadow.setAttribute('class', 'varwidthshadow')
        line_with_shadow.setAttribute('stroke-width', str(self._plain_stroke_width()))

        line_with_arrow = xml_map.createElement('line')
        line_with_arrow.setAttribute('x1', src_loc_x)
        line_with_arrow.setAttribute('y1', src_loc_y)
        line_with_arrow.setAttribute('x2', dest_loc_x)
        line_with_arrow.setAttribute('y2', dest_loc_y)
        line_with_arrow.setAttribute('class', 'varwidthorder')
        line_with_arrow.setAttribute('stroke', self.metadata['color'][power_name])
        line_with_arrow.setAttribute('stroke-width', str(self._colored_stroke_width()))
        line_with_arrow.setAttribute('marker-end', 'url(#arrow)')

        # Inserting
        g_node.appendChild(line_with_shadow)
        g_node.appendChild(line_with_arrow)
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' and _attr(child_node, 'id') == 'OrderLayer':
                for layer_node in child_node.childNodes:
                    if layer_node.nodeName == 'g' and _attr(layer_node, 'id') == 'Layer1':
                        layer_node.appendChild(g_node)
                        return xml_map

        # Returning
        return xml_map

    def _issue_support_move_order(self, xml_map, loc, src_loc, dest_loc, power_name):
        """ Issues a support move order

            :param xml_map: The xml map being generated
            :param loc: The location of the unit sending support (e.g. 'BER')
            :param src_loc: The location where the unit is moving from (e.g. 'PAR')
            :param dest_loc: The location where the unit is moving to (e.g. 'MAR')
            :param power_name: The power name issuing the move order
            :return: Nothing
        """
        loc_x, loc_y = self._get_unit_center(loc, False)
        src_loc_x, src_loc_y = self._get_unit_center(src_loc, False)
        dest_loc_x, dest_loc_y = self._get_unit_center(dest_loc, False)

        # Adjusting destination
        delta_x = dest_loc_x - src_loc_x
        delta_y = dest_loc_y - src_loc_y
        vector_length = (delta_x ** 2 + delta_y ** 2) ** 0.5
        delta_dec = float(self.metadata['symbol_size'][ARMY][1]) / 2 + 2 * self._colored_stroke_width()
        dest_loc_x = str(round(src_loc_x + (vector_length - delta_dec) / vector_length * delta_x, 2))
        dest_loc_y = str(round(src_loc_y + (vector_length - delta_dec) / vector_length * delta_y, 2))

        # Creating nodes
        g_node = xml_map.createElement('g')

        path_with_shadow = xml_map.createElement('path')
        path_with_shadow.setAttribute('class', 'shadowdash')
        path_with_shadow.setAttribute('d', 'M {x},{y} C {src_x},{src_y} {src_x},{src_y} {dest_x},{dest_y}'
                                      .format(x=loc_x,
                                              y=loc_y,
                                              src_x=src_loc_x,
                                              src_y=src_loc_y,
                                              dest_x=dest_loc_x,
                                              dest_y=dest_loc_y))

        path_with_arrow = xml_map.createElement('path')
        path_with_arrow.setAttribute('class', 'supportorder')
        path_with_arrow.setAttribute('stroke', self.metadata['color'][power_name])
        path_with_arrow.setAttribute('marker-end', 'url(#arrow)')
        path_with_arrow.setAttribute('d', 'M {x},{y} C {src_x},{src_y} {src_x},{src_y} {dest_x},{dest_y}'
                                     .format(x=loc_x,
                                             y=loc_y,
                                             src_x=src_loc_x,
                                             src_y=src_loc_y,
                                             dest_x=dest_loc_x,
                                             dest_y=dest_loc_y))

        # Inserting
        g_node.appendChild(path_with_shadow)
        g_node.appendChild(path_with_arrow)
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' and _attr(child_node, 'id') == 'OrderLayer':
                for layer_node in child_node.childNodes:
                    if layer_node.nodeName == 'g' and _attr(layer_node, 'id') == 'Layer2':
                        layer_node.appendChild(g_node)
                        return xml_map

        # Returning
        return xml_map

    def _issue_convoy_order(self, xml_map, loc, src_loc, dest_loc, power_name):
        """ Issues a convoy order

            :param xml_map: The xml map being generated
            :param loc: The location of the unit convoying (e.g. 'BER')
            :param src_loc: The location where the unit being convoyed is moving from (e.g. 'PAR')
            :param dest_loc: The location where the unit being convoyed is moving to (e.g. 'MAR')
            :param power_name: The power name issuing the convoy order
            :return: Nothing
        """
        symbol = 'ConvoyTriangle'
        symbol_loc_x, symbol_loc_y = self._center_symbol_around_unit(src_loc, False, symbol)
        symbol_height = float(self.metadata['symbol_size'][symbol][0])
        symbol_width = float(self.metadata['symbol_size'][symbol][1])
        triangle = EquilateralTriangle(x_top=float(symbol_loc_x) + symbol_width / 2,
                                       y_top=float(symbol_loc_y),
                                       x_right=float(symbol_loc_x) + symbol_width,
                                       y_right=float(symbol_loc_y) + symbol_height,
                                       x_left=float(symbol_loc_x),
                                       y_left=float(symbol_loc_y) + symbol_height)
        symbol_loc_y = str(float(symbol_loc_y) - float(self.metadata['symbol_size'][symbol][0]) / 6)

        loc_x, loc_y = self._get_unit_center(loc, False)
        src_loc_x, src_loc_y = self._get_unit_center(src_loc, False)
        dest_loc_x, dest_loc_y = self._get_unit_center(dest_loc, False)

        # Adjusting starting arrow (from convoy to start location)
        # This is to avoid the end of the arrow conflicting with the convoy triangle
        src_loc_x_1, src_loc_y_1 = triangle.intersection(loc_x, loc_y)
        src_loc_x_1 = str(src_loc_x_1)
        src_loc_y_1 = str(src_loc_y_1)

        # Adjusting destination arrow (from start location to destination location)
        # This is to avoid the start of the arrow conflicting with the convoy triangle
        src_loc_x_2, src_loc_y_2 = triangle.intersection(dest_loc_x, dest_loc_y)
        src_loc_x_2 = str(src_loc_x_2)
        src_loc_y_2 = str(src_loc_y_2)

        # Adjusting destination arrow (from start location to destination location)
        # This is to avoid the start of the arrow conflicting with the convoy triangle
        dest_delta_x = dest_loc_x - src_loc_x
        dest_delta_y = dest_loc_y - src_loc_y
        dest_vector_length = (dest_delta_x ** 2 + dest_delta_y ** 2) ** 0.5
        delta_dec = float(self.metadata['symbol_size'][ARMY][1]) / 2 + 2 * self._colored_stroke_width()
        dest_loc_x = str(round(src_loc_x + (dest_vector_length - delta_dec) / dest_vector_length * dest_delta_x, 2))
        dest_loc_y = str(round(src_loc_y + (dest_vector_length - delta_dec) / dest_vector_length * dest_delta_y, 2))

        loc_x = str(loc_x)
        loc_y = str(loc_y)

        # Generating convoy triangle node
        symbol_node = xml_map.createElement('use')
        symbol_node.setAttribute('x', symbol_loc_x)
        symbol_node.setAttribute('y', symbol_loc_y)
        symbol_node.setAttribute('height', self.metadata['symbol_size'][symbol][0])
        symbol_node.setAttribute('width', self.metadata['symbol_size'][symbol][1])
        symbol_node.setAttribute('xlink:href', '#{}'.format(symbol))

        # Creating nodes
        g_node = xml_map.createElement('g')
        g_node.setAttribute('stroke', self.metadata['color'][power_name])

        src_shadow_line = xml_map.createElement('line')
        src_shadow_line.setAttribute('x1', loc_x)
        src_shadow_line.setAttribute('y1', loc_y)
        src_shadow_line.setAttribute('x2', src_loc_x_1)
        src_shadow_line.setAttribute('y2', src_loc_y_1)
        src_shadow_line.setAttribute('class', 'shadowdash')

        src_convoy_line = xml_map.createElement('line')
        src_convoy_line.setAttribute('x1', loc_x)
        src_convoy_line.setAttribute('y1', loc_y)
        src_convoy_line.setAttribute('x2', src_loc_x_1)
        src_convoy_line.setAttribute('y2', src_loc_y_1)
        src_convoy_line.setAttribute('class', 'convoyorder')

        dest_shadow_line = xml_map.createElement('line')
        dest_shadow_line.setAttribute('x1', src_loc_x_2)
        dest_shadow_line.setAttribute('y1', src_loc_y_2)
        dest_shadow_line.setAttribute('x2', dest_loc_x)
        dest_shadow_line.setAttribute('y2', dest_loc_y)
        dest_shadow_line.setAttribute('class', 'shadowdash')

        dest_convoy_line = xml_map.createElement('line')
        dest_convoy_line.setAttribute('x1', src_loc_x_2)
        dest_convoy_line.setAttribute('y1', src_loc_y_2)
        dest_convoy_line.setAttribute('x2', dest_loc_x)
        dest_convoy_line.setAttribute('y2', dest_loc_y)
        dest_convoy_line.setAttribute('class', 'convoyorder')
        dest_convoy_line.setAttribute('marker-end', 'url(#arrow)')

        # Inserting
        g_node.appendChild(src_shadow_line)
        g_node.appendChild(dest_shadow_line)
        g_node.appendChild(src_convoy_line)
        g_node.appendChild(dest_convoy_line)
        g_node.appendChild(symbol_node)
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' and _attr(child_node, 'id') == 'OrderLayer':
                for layer_node in child_node.childNodes:
                    if layer_node.nodeName == 'g' and _attr(layer_node, 'id') == 'Layer2':
                        layer_node.appendChild(g_node)
                        return xml_map

        # Returning
        return xml_map

    def _issue_build_order(self, xml_map, unit_type, loc, power_name):
        """ Adds a build army/fleet order to the map

            :param xml_map: The xml map being generated
            :param unit_type: The unit type to build ('A' or 'F')
            :param loc: The province where the army is to be built (e.g. 'PAR')
            :param power_name: The name of the power building the unit
            :return: Nothing
        """
        # Symbols
        symbol = ARMY if unit_type == 'A' else FLEET
        build_symbol = 'BuildUnit'

        loc_x = self.metadata['coord'][loc]['unit'][0]
        loc_y = self.metadata['coord'][loc]['unit'][1]
        build_loc_x, build_loc_y = self._center_symbol_around_unit(loc, False, build_symbol)

        # Creating nodes
        g_node = xml_map.createElement('g')

        symbol_node = xml_map.createElement('use')
        symbol_node.setAttribute('x', loc_x)
        symbol_node.setAttribute('y', loc_y)
        symbol_node.setAttribute('height', self.metadata['symbol_size'][symbol][0])
        symbol_node.setAttribute('width', self.metadata['symbol_size'][symbol][1])
        symbol_node.setAttribute('xlink:href', '#{}'.format(symbol))
        symbol_node.setAttribute('class', 'unit{}'.format(power_name.lower()))

        build_node = xml_map.createElement('use')
        build_node.setAttribute('x', build_loc_x)
        build_node.setAttribute('y', build_loc_y)
        build_node.setAttribute('height', self.metadata['symbol_size'][build_symbol][0])
        build_node.setAttribute('width', self.metadata['symbol_size'][build_symbol][1])
        build_node.setAttribute('xlink:href', '#{}'.format(build_symbol))

        # Inserting
        g_node.appendChild(build_node)
        g_node.appendChild(symbol_node)
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' and _attr(child_node, 'id') == 'HighestOrderLayer':
                child_node.appendChild(g_node)
                return xml_map

        # Returning
        return xml_map

    def _issue_disband_order(self, xml_map, loc):
        """ Adds a disband order to the map

            :param xml_map: The xml map being generated
            :param loc: The province where the unit is disbanded (e.g. 'PAR')
            :return: Nothing
        """
        # Symbols
        symbol = 'RemoveUnit'
        loc_x, loc_y = self._center_symbol_around_unit(loc, self.game.get_current_phase()[-1] == 'R', symbol)

        # Creating nodes
        g_node = xml_map.createElement('g')
        symbol_node = xml_map.createElement('use')
        symbol_node.setAttribute('x', loc_x)
        symbol_node.setAttribute('y', loc_y)
        symbol_node.setAttribute('height', self.metadata['symbol_size'][symbol][0])
        symbol_node.setAttribute('width', self.metadata['symbol_size'][symbol][1])
        symbol_node.setAttribute('xlink:href', '#{}'.format(symbol))

        # Inserting
        g_node.appendChild(symbol_node)
        for child_node in xml_map.getElementsByTagName('svg')[0].childNodes:
            if child_node.nodeName == 'g' and _attr(child_node, 'id') == 'HighestOrderLayer':
                child_node.appendChild(g_node)
                return xml_map

        # Returning
        return xml_map

    def _center_symbol_around_unit(self, loc, is_dislodged, symbol):        # type: (str, bool, str) -> Tuple[str, str]
        """ Compute top-left coordinates of a symbol to be centered around a unit.

            :param loc: unit location (e.g. 'PAR')
            :param is_dislodged: boolean to tell if unit is dislodged
            :param symbol: symbol identifier (e.g. 'HoldUnit')
            :return: a couple of coordinates (x, y) as string values
        """
        key = 'disl' if is_dislodged else 'unit'
        unit_x, unit_y = self.metadata['coord'][loc][key]
        unit_height, unit_width = self.metadata['symbol_size'][ARMY]
        symbol_height, symbol_width = self.metadata['symbol_size'][symbol]
        return (
            str(float(unit_x) + float(unit_width) / 2 - float(symbol_width) / 2),
            str(float(unit_y) + float(unit_height) / 2 - float(symbol_height) / 2)
        )

    def _get_unit_center(self, loc, is_dislodged):                          # type: (str, bool) -> Tuple[float, float]
        """ Compute coordinates of unit center.

            :param loc: unit location
            :param is_dislodged: boolean to tell if unit is dislodged
            :return: a couple of coordinates (x, y) as floating values
        """
        unit_x, unit_y = self.metadata['coord'][loc]['disl' if is_dislodged else 'unit']
        unit_height, unit_width = self.metadata['symbol_size'][ARMY]
        return (
            float(unit_x) + float(unit_width) / 2,
            float(unit_y) + float(unit_height) / 2
        )

    def _plain_stroke_width(self):                                          # type: () -> float
        """ Return generic stroke width for plain lines.

            :return: stroke width as floating value.
        """
        return float(self.metadata['symbol_size']['Stroke'][0])

    def _colored_stroke_width(self):                                        # type: () -> float
        """ Return generic stroke width for colored or textured lines.

            :return: stroke width as floating value.
        """
        return float(self.metadata['symbol_size']['Stroke'][1])
