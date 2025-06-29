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
import {centerSymbolAroundUnit} from "./common";
import PropTypes from "prop-types";

export class Hold extends React.Component {
    render() {
        const Coordinates = this.props.coordinates;
        const Colors = this.props.colors;
        const SymbolSizes = this.props.symbolSizes;
        const symbol = 'HoldUnit';
        const [loc_x, loc_y] = centerSymbolAroundUnit(Coordinates, SymbolSizes, this.props.loc, false, symbol);
        return (
            <g stroke={Colors[this.props.powerName]}>
                <use
                    x={loc_x}
                    y={loc_y}
                    width={SymbolSizes[symbol].width}
                    height={SymbolSizes[symbol].height}
                    href={`#${symbol}`}/>
            </g>
        );
    }
}

Hold.propTypes = {
    loc: PropTypes.string.isRequired,
    powerName: PropTypes.string.isRequired,
    coordinates: PropTypes.object.isRequired,
    symbolSizes: PropTypes.object.isRequired,
    colors: PropTypes.object.isRequired
};
