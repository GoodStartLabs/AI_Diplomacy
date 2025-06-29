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
import {centerSymbolAroundUnit, getUnitCenter} from "./common";
import PropTypes from "prop-types";

export class SupportHold extends React.Component {
    render() {
        const Coordinates = this.props.coordinates;
        const SymbolSizes = this.props.symbolSizes;
        const Colors = this.props.colors;
        const loc = this.props.loc;
        const dest_loc = this.props.dstLoc;
        const symbol = 'SupportHoldUnit';
        const [symbol_loc_x, symbol_loc_y] = centerSymbolAroundUnit(Coordinates, SymbolSizes, dest_loc, false, symbol);
        const [loc_x, loc_y] = getUnitCenter(Coordinates, SymbolSizes, loc, false);
        let [dest_loc_x, dest_loc_y] = getUnitCenter(Coordinates, SymbolSizes, dest_loc, false);

        const delta_x = dest_loc_x - loc_x;
        const delta_y = dest_loc_y - loc_y;
        const vector_length = Math.sqrt(delta_x * delta_x + delta_y * delta_y);
        const delta_dec = parseFloat(SymbolSizes[symbol].height) / 2;
        dest_loc_x = '' + Math.round((parseFloat(loc_x) + (vector_length - delta_dec) / vector_length * delta_x) * 100.) / 100.;
        dest_loc_y = '' + Math.round((parseFloat(loc_y) + (vector_length - delta_dec) / vector_length * delta_y) * 100.) / 100.;

        return (
            <g stroke={Colors[this.props.powerName]}>
                <line x1={loc_x}
                      y1={loc_y}
                      x2={dest_loc_x}
                      y2={dest_loc_y}
                      className={'shadowdash'}/>
                <line x1={loc_x}
                      y1={loc_y}
                      x2={dest_loc_x}
                      y2={dest_loc_y}
                      className={'supportorder'}
                      stroke={Colors[this.props.powerName]}/>
                <use
                    x={symbol_loc_x}
                    y={symbol_loc_y}
                    width={SymbolSizes[symbol].width}
                    height={SymbolSizes[symbol].height}
                    href={`#${symbol}`}
                />
            </g>
        );
    }
}

SupportHold.propTypes = {
    loc: PropTypes.string.isRequired,
    dstLoc: PropTypes.string.isRequired,
    powerName: PropTypes.string.isRequired,
    coordinates: PropTypes.object.isRequired,
    symbolSizes: PropTypes.object.isRequired,
    colors: PropTypes.object.isRequired
};
