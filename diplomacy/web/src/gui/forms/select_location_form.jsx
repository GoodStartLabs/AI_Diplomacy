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
import PropTypes from "prop-types";
import {Button} from "../components/button";
import {FancyBox} from "../components/fancyBox";

export class SelectLocationForm extends React.Component {
    render() {
        const title = `Select location to continue building order: ${this.props.path.join(' ')}`;
        return (
            <FancyBox title={title} onClose={this.props.onClose}>
                <div>
                    {this.props.locations.map((location, index) => (
                        <Button key={index} title={location} large={true}
                                onClick={() => this.props.onSelect(location)}/>
                    ))}
                </div>
            </FancyBox>
        );
    }
}

SelectLocationForm.propTypes = {
    locations: PropTypes.arrayOf(PropTypes.string).isRequired,
    onSelect: PropTypes.func.isRequired, // onSelect(location)
    onClose: PropTypes.func.isRequired,
    path: PropTypes.array.isRequired
};
