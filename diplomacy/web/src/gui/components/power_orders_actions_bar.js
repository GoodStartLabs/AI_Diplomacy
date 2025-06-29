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
import {Button} from "./button";
import {Bar} from "./layouts";
import PropTypes from 'prop-types';

export class PowerOrdersActionBar extends React.Component {
    render() {
        return (
            <Bar className={'p-2'}>
                <strong className={'mr-4'}>Orders:</strong>
                <Button title={'reset'} onClick={this.props.onReset}/>
                <Button title={'delete all'} onClick={this.props.onDeleteAll}/>
                <Button color={'primary'} title={'update'} onClick={this.props.onUpdate}/>
                {(this.props.onProcess &&
                    <Button color={'danger'} title={'process game'} onClick={this.props.onProcess}/>) || ''}
            </Bar>
        );
    }
}

PowerOrdersActionBar.propTypes = {
    onReset: PropTypes.func.isRequired,
    onDeleteAll: PropTypes.func.isRequired,
    onUpdate: PropTypes.func.isRequired,
    onProcess: PropTypes.func
};
