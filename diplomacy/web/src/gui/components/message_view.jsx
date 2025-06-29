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

export class MessageView extends React.Component {
    // message
    render() {
        const message = this.props.message;
        const owner = this.props.owner;
        const id = this.props.id ? {id: this.props.id} : {};
        const messagesLines = message.message.replace('\r\n', '\n')
            .replace('\r', '\n')
            .replace('<br>', '\n')
            .replace('<br/>', '\n')
            .split('\n');
        let onClick = null;
        const classNames = ['game-message', 'row'];
        if (owner === message.sender)
            classNames.push('message-sender');
        else {
            classNames.push('message-recipient');
            if (message.read || this.props.read)
                classNames.push('message-read');
            onClick = this.props.onClick ? {onClick: () => this.props.onClick(message)} : {};
        }
        return (
            <div className={'game-message-wrapper' + (
                this.props.phase && this.props.phase !== message.phase ? ' other-phase' : ' new-phase')}
                 {...id}>
                <div className={classNames.join(' ')} {...onClick}>
                    <div className="message-header col-md-auto text-md-right text-center">
                        {message.phase}
                    </div>
                    <div className="message-content col-md">
                        {messagesLines.map((line, lineIndex) => <div key={lineIndex}>{
                            line.replace(/(<([^>]+)>)/ig, "")
                        }</div>)}
                    </div>
                </div>
            </div>
        );
    }
}

MessageView.propTypes = {
    message: PropTypes.object,
    phase: PropTypes.string,
    owner: PropTypes.string,
    onClick: PropTypes.func,
    id: PropTypes.string,
    read: PropTypes.bool
};
