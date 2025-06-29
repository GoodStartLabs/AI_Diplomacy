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
import {ARMY, coloredStrokeWidth, getUnitCenter, plainStrokeWidth} from "./common";
import PropTypes from "prop-types";

export class Move extends React.Component {
    render() {
        const Coordinates = this.props.coordinates;
        const SymbolSizes = this.props.symbolSizes;
        const Colors = this.props.colors;
        const src_loc = this.props.srcLoc;
        const dest_loc = this.props.dstLoc;
        const is_dislodged = this.props.phaseType === 'R';
        const [src_loc_x, src_loc_y] = getUnitCenter(Coordinates, SymbolSizes, src_loc, is_dislodged);
        let [dest_loc_x, dest_loc_y] = getUnitCenter(Coordinates, SymbolSizes, dest_loc, is_dislodged);
        // Adjusting destination
        const delta_x = dest_loc_x - src_loc_x;
        const delta_y = dest_loc_y - src_loc_y;
        const vector_length = Math.sqrt(delta_x * delta_x + delta_y * delta_y);
        const delta_dec = parseFloat(SymbolSizes[ARMY].width) / 2 + 2 * coloredStrokeWidth(SymbolSizes);
        dest_loc_x = '' + Math.round((parseFloat(src_loc_x) + (vector_length - delta_dec) / vector_length * delta_x) * 100.) / 100.;
        dest_loc_y = '' + Math.round((parseFloat(src_loc_y) + (vector_length - delta_dec) / vector_length * delta_y) * 100.) / 100.;
        return (
            <g>
                <line x1={src_loc_x}
                      y1={src_loc_y}
                      x2={dest_loc_x}
                      y2={dest_loc_y}
                      className={'varwidthshadow'}
                      strokeWidth={'' + plainStrokeWidth(SymbolSizes)}/>
                <line x1={src_loc_x}
                      y1={src_loc_y}
                      x2={dest_loc_x}
                      y2={dest_loc_y}
                      className={'varwidthorder'}
                      markerEnd={'url(#arrow)'}
                      stroke={Colors[this.props.powerName]}
                      strokeWidth={'' + coloredStrokeWidth(SymbolSizes)}/>
            </g>
        );
    }
}

Move.propTypes = {
    srcLoc: PropTypes.string.isRequired,
    dstLoc: PropTypes.string.isRequired,
    powerName: PropTypes.string.isRequired,
    phaseType: PropTypes.string.isRequired,
    coordinates: PropTypes.object.isRequired,
    symbolSizes: PropTypes.object.isRequired,
    colors: PropTypes.object.isRequired
};
