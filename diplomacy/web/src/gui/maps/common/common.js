// ==============================================================================
// Copyright (C) 2019 - Philip Paquette, Steven Bocco
//
//  This program is free software: you can redistribute it and/or modify it under
//  the terms of the GNU Affero General Public License as published by the Free
//  Software Foundation, either version 3 of the License, or (at your option) any
//  later version.
//
//  This program is distributed in the hope that it will be useful, but WITHOUT
//  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
//  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
//  details.
//
//  You should have received a copy of the GNU Affero General Public License along
//  with this program.  If not, see <https://www.gnu.org/licenses/>.
// ==============================================================================

export const ARMY = 'Army';
export const FLEET = 'Fleet';

export function offset(floatString, offset) {
    return "" + (parseFloat(floatString) + offset);
}

export function setInfluence(classes, mapData, loc, power_name) {
    const province = mapData.getProvince(loc);
    if (!province)
        throw new Error(`Unable to find province ${loc}`);
    if (!['LAND', 'COAST'].includes(province.type))
        return;
    const id = province.getID(classes);
    if (!id)
        throw new Error(`Unable to find SVG path for loc ${id}`);
    classes[id] = power_name ? power_name.toLowerCase() : 'nopower';
}

export function getClickedID(event) {
    let node = event.target;
    if (!node.id && node.parentNode.id && node.parentNode.tagName === 'g')
        node = node.parentNode;
    let id = node.id;
    return id ? id.substr(0, 3) : null;
}

export function parseLocation(txt) {
    if (txt.length > 2 && txt[1] === ' ' && ['A', 'F'].includes(txt[0]))
        return txt.substr(2);
    return txt;
}

export function centerSymbolAroundUnit(coordinates, symbolSizes, loc, isDislodged, symbol) {
    const key = isDislodged ? 'disl' : 'unit';
    const unitKey = ARMY;
    const [unit_x, unit_y] = coordinates[loc][key];
    const unit_height = symbolSizes[unitKey].height;
    const unit_width = symbolSizes[unitKey].width;
    const symbol_height = symbolSizes[symbol].height;
    const symbol_width = symbolSizes[symbol].width;
    return [
        `${(parseFloat(unit_x) + parseFloat(unit_width) / 2 - parseFloat(symbol_width) / 2)}`,
        `${(parseFloat(unit_y) + parseFloat(unit_height) / 2 - parseFloat(symbol_height) / 2)}`
    ];
}

export function getUnitCenter(coordinates, symbolSizes, loc, isDislodged) {
    const key = isDislodged ? 'disl' : 'unit';
    const unitKey = ARMY;
    const [unit_x, unit_y] = coordinates[loc][key];
    const unit_height = symbolSizes[unitKey].height;
    const unit_width = symbolSizes[unitKey].width;
    return [
        `${parseFloat(unit_x) + parseFloat(unit_width) / 2}`,
        `${parseFloat(unit_y) + parseFloat(unit_height) / 2}`
    ];
}

export function plainStrokeWidth(symbolSizes) {
    return parseFloat(symbolSizes.Stroke.height);
}

export function coloredStrokeWidth(symbolSizes) {
    return parseFloat(symbolSizes.Stroke.width);
}
