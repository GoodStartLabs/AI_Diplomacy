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
import React from "react";
import {ARMY, centerSymbolAroundUnit, coloredStrokeWidth, getUnitCenter} from "./common";
import {EquilateralTriangle} from "./equilateralTriangle";
import PropTypes from "prop-types";

export class Convoy extends React.Component {
    render() {
        const Coordinates = this.props.coordinates;
        const SymbolSizes = this.props.symbolSizes;
        const Colors = this.props.colors;
        const loc = this.props.loc;
        const src_loc = this.props.srcLoc;
        const dest_loc = this.props.dstLoc;

        const symbol = 'ConvoyTriangle';
        let [symbol_loc_x, symbol_loc_y] = centerSymbolAroundUnit(Coordinates, SymbolSizes, src_loc, false, symbol);
        const symbol_height = parseFloat(SymbolSizes[symbol].height);
        const symbol_width = parseFloat(SymbolSizes[symbol].width);
        const triangle = new EquilateralTriangle(
            parseFloat(symbol_loc_x) + symbol_width / 2,
            parseFloat(symbol_loc_y),
            parseFloat(symbol_loc_x) + symbol_width,
            parseFloat(symbol_loc_y) + symbol_height,
            parseFloat(symbol_loc_x),
            parseFloat(symbol_loc_y) + symbol_height
        );
        symbol_loc_y = '' + (parseFloat(symbol_loc_y) - symbol_height / 6);
        const [loc_x, loc_y] = getUnitCenter(Coordinates, SymbolSizes, loc, false);
        const [src_loc_x, src_loc_y] = getUnitCenter(Coordinates, SymbolSizes, src_loc, false);
        let [dest_loc_x, dest_loc_y] = getUnitCenter(Coordinates, SymbolSizes, dest_loc, false);

        const [src_loc_x_1, src_loc_y_1] = triangle.intersection(loc_x, loc_y);
        const [src_loc_x_2, src_loc_y_2] = triangle.intersection(dest_loc_x, dest_loc_y);

        const dest_delta_x = dest_loc_x - src_loc_x;
        const dest_delta_y = dest_loc_y - src_loc_y;
        const dest_vector_length = Math.sqrt(dest_delta_x * dest_delta_x + dest_delta_y * dest_delta_y);
        const delta_dec = parseFloat(SymbolSizes[ARMY].width) / 2 + 2 * coloredStrokeWidth(SymbolSizes);
        dest_loc_x = '' + Math.round((parseFloat(src_loc_x) + (dest_vector_length - delta_dec) / dest_vector_length * dest_delta_x) * 100.) / 100.;
        dest_loc_y = '' + Math.round((parseFloat(src_loc_y) + (dest_vector_length - delta_dec) / dest_vector_length * dest_delta_y) * 100.) / 100.;

        return (
            <g stroke={Colors[this.props.powerName]}>
                <line x1={loc_x}
                      y1={loc_y}
                      x2={src_loc_x_1}
                      y2={src_loc_y_1}
                      className={'shadowdash'}/>
                <line x1={src_loc_x_2}
                      y1={src_loc_y_2}
                      x2={dest_loc_x}
                      y2={dest_loc_y}
                      className={'shadowdash'}/>
                <line x1={loc_x}
                      y1={loc_y}
                      x2={src_loc_x_1}
                      y2={src_loc_y_1}
                      className={'convoyorder'}
                      stroke={Colors[this.props.powerName]}/>
                <line x1={src_loc_x_2}
                      y1={src_loc_y_2}
                      x2={dest_loc_x}
                      y2={dest_loc_y}
                      className={'convoyorder'}
                      markerEnd={'url(#arrow)'}
                      stroke={Colors[this.props.powerName]}/>
                <use
                    x={symbol_loc_x}
                    y={symbol_loc_y}
                    width={'' + symbol_width}
                    height={'' + symbol_height}
                    href={`#${symbol}`}
                />
            </g>
        );
    }
}

Convoy.propTypes = {
    loc: PropTypes.string.isRequired,
    srcLoc: PropTypes.string.isRequired,
    dstLoc: PropTypes.string.isRequired,
    powerName: PropTypes.string.isRequired,
    coordinates: PropTypes.object.isRequired,
    symbolSizes: PropTypes.object.isRequired,
    colors: PropTypes.object.isRequired
};
