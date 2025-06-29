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
import {Forms} from "../components/forms";
import {UTILS} from "../../diplomacy/utils/utils";
import PropTypes from "prop-types";

export class MessageForm extends React.Component {
    constructor(props) {
        super(props);
        this.state = this.initState();
    }

    initState() {
        return {message: ''};
    }

    render() {
        const onChange = Forms.createOnChangeCallback(this, this.props.onChange);
        const onSubmit = Forms.createOnSubmitCallback(this, this.props.onSubmit, this.initState());
        return (
            <form>
                <div className={'form-group'}>
                    {Forms.createLabel('message', '', 'sr-only')}
                    <textarea id={'message'} className={'form-control'}
                              value={Forms.getValue(this.state, 'message')} onChange={onChange}/>
                </div>
                {Forms.createSubmit(`send (${this.props.sender} ${UTILS.html.UNICODE_SMALL_RIGHT_ARROW} ${this.props.recipient})`, true, onSubmit)}
            </form>
        );
    }
}

MessageForm.propTypes = {
    sender: PropTypes.string,
    recipient: PropTypes.string,
    onChange: PropTypes.func,
    onSubmit: PropTypes.func
};
