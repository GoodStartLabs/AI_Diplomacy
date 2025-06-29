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
import {ARMY, coloredStrokeWidth, getUnitCenter} from "./common";
import PropTypes from "prop-types";

export class SupportMove extends React.Component {
    render() {
        const Coordinates = this.props.coordinates;
        const SymbolSizes = this.props.symbolSizes;
        const Colors = this.props.colors;
        const loc = this.props.loc;
        const src_loc = this.props.srcLoc;
        const dest_loc = this.props.dstLoc;
        const [loc_x, loc_y] = getUnitCenter(Coordinates, SymbolSizes, loc, false);
        const [src_loc_x, src_loc_y] = getUnitCenter(Coordinates, SymbolSizes, src_loc, false);
        let [dest_loc_x, dest_loc_y] = getUnitCenter(Coordinates, SymbolSizes, dest_loc, false);

        // Adjusting destination
        const delta_x = dest_loc_x - src_loc_x;
        const delta_y = dest_loc_y - src_loc_y;
        const vector_length = Math.sqrt(delta_x * delta_x + delta_y * delta_y);
        const delta_dec = parseFloat(SymbolSizes[ARMY].width) / 2 + 2 * coloredStrokeWidth(SymbolSizes);
        dest_loc_x = '' + Math.round((parseFloat(src_loc_x) + (vector_length - delta_dec) / vector_length * delta_x) * 100.) / 100.;
        dest_loc_y = '' + Math.round((parseFloat(src_loc_y) + (vector_length - delta_dec) / vector_length * delta_y) * 100.) / 100.;
        return (
            <g>
                <path className={'shadowdash'}
                      d={`M ${loc_x},${loc_y} C ${src_loc_x},${src_loc_y} ${src_loc_x},${src_loc_y} ${dest_loc_x},${dest_loc_y}`}/>
                <path className={'supportorder'}
                      markerEnd={'url(#arrow)'}
                      stroke={Colors[this.props.powerName]}
                      d={`M ${loc_x},${loc_y} C ${src_loc_x},${src_loc_y} ${src_loc_x},${src_loc_y} ${dest_loc_x},${dest_loc_y}`}/>
            </g>
        );
    }
}

SupportMove.propTypes = {
    loc: PropTypes.string.isRequired,
    srcLoc: PropTypes.string.isRequired,
    dstLoc: PropTypes.string.isRequired,
    powerName: PropTypes.string.isRequired,
    coordinates: PropTypes.object.isRequired,
    symbolSizes: PropTypes.object.isRequired,
    colors: PropTypes.object.isRequired
};
