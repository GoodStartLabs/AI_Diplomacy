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
import {DipStorage} from "../utils/dipStorage";

export class ConnectionForm extends React.Component {
    constructor(props) {
        super(props);
        // Load fields values from local storage.
        const initialState = this.initState();
        const savedState = DipStorage.getConnectionForm();
        if (savedState) {
            if (savedState.hostname)
                initialState.hostname = savedState.hostname;
            if (savedState.port)
                initialState.port = savedState.port;
            if (savedState.username)
                initialState.username = savedState.username;
            if (savedState.showServerFields)
                initialState.showServerFields = savedState.showServerFields;
        }
        this.state = initialState;
        this.updateServerFieldsView = this.updateServerFieldsView.bind(this);
        this.onChange = this.onChange.bind(this);
    }

    initState() {
        return {
            hostname: window.location.hostname,
            port: (window.location.protocol.toLowerCase() === 'https:') ? 8433 : 8432,
            username: '',
            password: '',
            showServerFields: false
        };
    }

    updateServerFieldsView() {
        DipStorage.setConnectionshowServerFields(!this.state.showServerFields);
        this.setState({showServerFields: !this.state.showServerFields});
    }

    onChange(newState) {
        const initialState = this.initState();
        if (newState.hostname !== initialState.hostname)
            DipStorage.setConnectionHostname(newState.hostname);
        else
            DipStorage.setConnectionHostname(null);
        if (newState.port !== initialState.port)
            DipStorage.setConnectionPort(newState.port);
        else
            DipStorage.setConnectionPort(null);
        if (newState.username !== initialState.username)
            DipStorage.setConnectionUsername(newState.username);
        else
            DipStorage.setConnectionUsername(null);
        if (this.props.onChange)
            this.props.onChange(newState);
    }

    render() {
        const onChange = Forms.createOnChangeCallback(this, this.onChange);
        const onSubmit = Forms.createOnSubmitCallback(this, this.props.onSubmit);
        return (
            <form>
                {Forms.createRow(
                    Forms.createColLabel('username', 'username:'),
                    <input className={'form-control'} type={'text'} id={'username'}
                           value={Forms.getValue(this.state, 'username')} onChange={onChange}/>
                )}
                {Forms.createRow(
                    Forms.createColLabel('password', 'password:'),
                    <input className={'form-control'} type={'password'} id={'password'}
                           value={Forms.getValue(this.state, 'password')} onChange={onChange}/>
                )}
                <div>
                    <div className={this.state.showServerFields ? 'mb-2' : 'mb-4'}>
                    <span className={'button-server'} onClick={this.updateServerFieldsView}>
                        server settings {this.state.showServerFields ? UTILS.html.UNICODE_BOTTOM_ARROW : UTILS.html.UNICODE_TOP_ARROW}
                    </span>
                    </div>
                    {this.state.showServerFields && (
                        <div className={'mb-4'}>
                            {Forms.createRow(
                                <label className={'col'} htmlFor={'hostname'}>hostname:</label>,
                                <input className={'form-control'} type={'text'} id={'hostname'}
                                       value={Forms.getValue(this.state, 'hostname')} onChange={onChange}/>
                            )}
                            {Forms.createRow(
                                <label className={'col'} htmlFor={'port'}>port:</label>,
                                <input className={'form-control'} type={'number'} id={'port'}
                                       value={Forms.getValue(this.state, 'port')}
                                       onChange={onChange}/>
                            )}
                        </div>
                    )}
                </div>
                {Forms.createRow('', Forms.createSubmit('connect', true, onSubmit))}
            </form>
        );
    }
}

ConnectionForm.propTypes = {
    onChange: PropTypes.func,
    onSubmit: PropTypes.func
};
