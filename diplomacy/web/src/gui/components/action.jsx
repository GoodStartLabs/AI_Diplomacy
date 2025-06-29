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


export class Action extends React.Component {
    // title
    // isActive
    // onClick
    // See Button parameters.

    render() {
        return (
            <div className="action nav-item" onClick={this.props.onClick}>
                <div
                    className={'nav-link' + (this.props.isActive ? ' active' : '') + (this.props.highlight !== null ? ' updated' : '')}>
                    {this.props.title}
                    {this.props.highlight !== null
                    && this.props.highlight !== undefined
                    && <span className={'update'}>{this.props.highlight}</span>}
                </div>
            </div>
        );
    }
}

Action.propTypes = {
    title: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired,
    highlight: PropTypes.any,
    isActive: PropTypes.bool
};

Action.defaultProps = {
    highlight: null,
    isActive: false
};
