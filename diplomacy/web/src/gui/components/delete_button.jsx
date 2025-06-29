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
import {Button} from "./button";
import PropTypes from "prop-types";

export class DeleteButton extends React.Component {
    constructor(props) {
        super(props);
        this.state = {step: 0};
        this.onClick = this.onClick.bind(this);
    }

    onClick() {
        this.setState({step: this.state.step + 1}, () => {
            if (this.state.step === 2)
                this.props.onClick();
        });
    }

    render() {
        let title = '';
        let color = '';
        if (this.state.step === 0) {
            title = this.props.title;
            color = 'secondary';
        } else if (this.state.step === 1) {
            title = this.props.confirmTitle;
            color = 'danger';
        } else if (this.state.step === 2) {
            title = this.props.waitingTitle;
            color = 'danger';
        }
        return (
            <Button title={title} color={color} onClick={this.onClick} small={true} large={true}/>
        );
    }
}

DeleteButton.propTypes = {
    title: PropTypes.string.isRequired,
    confirmTitle: PropTypes.string.isRequired,
    waitingTitle: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired
};
