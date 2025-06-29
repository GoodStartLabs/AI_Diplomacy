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
import {ARMY, FLEET} from "./common";
import PropTypes from "prop-types";

export class Unit extends React.Component {
    render() {
        const Coordinates = this.props.coordinates;
        const SymbolSizes = this.props.symbolSizes;
        const split_unit = this.props.unit.split(/ +/);
        const unit_type = split_unit[0];
        const loc = split_unit[1];
        const dislogged_type = this.props.isDislodged ? 'disl' : 'unit';
        const symbol = unit_type === 'F' ? FLEET : ARMY;
        const loc_x = Coordinates[loc][dislogged_type][0];
        const loc_y = Coordinates[loc][dislogged_type][1];
        return (
            <use href={`#${this.props.isDislodged ? 'Dislodged' : ''}${symbol}`}
                 x={loc_x}
                 y={loc_y}
                 id={`${this.props.isDislodged ? 'dislodged_' : ''}unit_${loc}`}
                 width={SymbolSizes[symbol].width}
                 height={SymbolSizes[symbol].height}
                 className={`unit${this.props.powerName.toLowerCase()}`}/>
        );
    }
}

Unit.propTypes = {
    unit: PropTypes.string.isRequired,
    powerName: PropTypes.string.isRequired,
    isDislodged: PropTypes.bool.isRequired,
    coordinates: PropTypes.object.isRequired,
    symbolSizes: PropTypes.object.isRequired
};
