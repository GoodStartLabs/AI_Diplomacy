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
import React from 'react';
import PropTypes from 'prop-types';
import {Button} from "./button";

const TIMES = '\u00D7';

export class FancyBox extends React.Component {
    render() {
        return (
            <div className="fancy-box">
                <div className="fancy-bar p-1 d-flex flex-row">
                    <div
                        className="flex-grow-1 fancy-title d-flex flex-column justify-content-center pr-0 pr-sm-1">{this.props.title}</div>
                    <div className="fancy-button">
                        <Button title={TIMES} color={'danger'} onClick={this.props.onClose}/>
                    </div>
                </div>
                <div className="fancy-content p-2">
                    {this.props.children}
                </div>
            </div>
        );
    }
}


FancyBox.propTypes = {
    title: PropTypes.string.isRequired,
    onClose: PropTypes.func.isRequired,
    children: PropTypes.any.isRequired
};
