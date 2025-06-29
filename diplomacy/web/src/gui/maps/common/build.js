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
import {ARMY, centerSymbolAroundUnit, FLEET} from "./common";
import PropTypes from "prop-types";

export class Build extends React.Component {
    render() {
        const Coordinates = this.props.coordinates;
        const SymbolSizes = this.props.symbolSizes;
        const loc = this.props.loc;
        const unit_type = this.props.unitType;
        const build_symbol = 'BuildUnit';
        const loc_x = Coordinates[loc].unit[0];
        const loc_y = Coordinates[loc].unit[1];
        const [build_loc_x, build_loc_y] = centerSymbolAroundUnit(Coordinates, SymbolSizes, loc, false, build_symbol);

        const symbol = unit_type === 'A' ? ARMY : FLEET;
        return (
            <g>
                <use x={build_loc_x}
                     y={build_loc_y}
                     height={SymbolSizes[build_symbol].height}
                     width={SymbolSizes[build_symbol].width}
                     href={`#${build_symbol}`}/>
                <use x={loc_x}
                     y={loc_y}
                     height={SymbolSizes[symbol].height}
                     width={SymbolSizes[symbol].width}
                     href={`#${symbol}`}
                     className={`unit${this.props.powerName.toLowerCase()}`}/>
            </g>
        );
    }
}

Build.propTypes = {
    unitType: PropTypes.string.isRequired,
    loc: PropTypes.string.isRequired,
    powerName: PropTypes.string.isRequired,
    coordinates: PropTypes.object.isRequired,
    symbolSizes: PropTypes.object.isRequired
};
