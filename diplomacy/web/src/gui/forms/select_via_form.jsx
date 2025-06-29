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

const HotKey = require('react-shortcut');

export class SelectViaForm extends React.Component {
    render() {
        return (
            <FancyBox title={`Select move type for move order: ${this.props.path.join(' ')}`}
                      onClose={this.props.onClose}>
                <div>
                    <Button title={'regular move (M)'} large={true} onClick={() => this.props.onSelect('M')}/>
                    <Button title={'move via (V)'} large={true} onClick={() => this.props.onSelect('V')}/>
                    <HotKey keys={['m']} onKeysCoincide={() => this.props.onSelect('M')}/>
                    <HotKey keys={['v']} onKeysCoincide={() => this.props.onSelect('V')}/>
                </div>
            </FancyBox>
        );
    }
}

SelectViaForm.propTypes = {
    path: PropTypes.array.isRequired,
    onSelect: PropTypes.func.isRequired,
    onClose: PropTypes.func.isRequired
};

