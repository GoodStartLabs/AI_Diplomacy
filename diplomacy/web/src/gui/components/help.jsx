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
import PropTypes from 'prop-types';
import {FancyBox} from "./fancyBox";

export class Help extends React.Component {
    render() {
        return (
            <FancyBox title={'Help'} onClose={this.props.onClose}>
                <div>
                    <p>When building an order, press <strong>ESC</strong> to reset build.</p>
                    <p>Press letter associated to an order type to start building an order of this type.
                        <br/> Order type letter is indicated in order type name after order type radio button.
                    </p>
                    <p>In Phase History tab, use keyboard left and right arrows to navigate in past phases.</p>
                </div>
            </FancyBox>
        );
    }
}

Help.propTypes = {
    onClose: PropTypes.func.isRequired
};
