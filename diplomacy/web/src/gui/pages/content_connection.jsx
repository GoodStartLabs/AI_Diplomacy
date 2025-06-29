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
import {Connection} from "../../diplomacy/client/connection";
import {ConnectionForm} from "../forms/connection_form";
import {DipStorage} from "../utils/dipStorage";
import {Helmet} from "react-helmet";
import {Navigation} from "../components/navigation";
import {PageContext} from "../components/page_context";

export class ContentConnection extends React.Component {
    constructor(props) {
        super(props);
        this.connection = null;
        this.onSubmit = this.onSubmit.bind(this);
    }

    onSubmit(data) {
        const page = this.context;
        for (let fieldName of ['hostname', 'port', 'username', 'password', 'showServerFields'])
            if (!data.hasOwnProperty(fieldName))
                return page.error(`Missing ${fieldName}, got ${JSON.stringify(data)}`);
        page.info('Connecting ...');
        if (this.connection) {
            this.connection.currentConnectionProcessing.stop();
        }
        this.connection = new Connection(data.hostname, data.port, window.location.protocol.toLowerCase() === 'https:');
        this.connection.onReconnectionError = page.onReconnectionError;
        // Page is passed as logger object (with methods info(), error(), success()) when connecting.
        this.connection.connect(page)
            .then(() => {
                page.connection = this.connection;
                this.connection = null;
                page.success(`Successfully connected to server ${data.username}:${data.port}`);
                page.connection.authenticate(data.username, data.password)
                    .then((channel) => {
                        page.channel = channel;
                        return channel.getAvailableMaps();
                    })
                    .then(availableMaps => {
                        for (let mapName of Object.keys(availableMaps))
                            availableMaps[mapName].powers.sort();
                        page.availableMaps = availableMaps;
                        const userGameIndices = DipStorage.getUserGames(page.channel.username);
                        if (userGameIndices && userGameIndices.length) {
                            return page.channel.getGamesInfo({games: userGameIndices});
                        } else {
                            return null;
                        }
                    })
                    .then((gamesInfo) => {
                        if (gamesInfo) {
                            page.success('Found ' + gamesInfo.length + ' user games.');
                            page.updateMyGames(gamesInfo);
                        }
                        page.loadGames({success: `Account ${data.username} connected.`});
                    })
                    .catch((error) => {
                        page.error('Error while authenticating: ' + error + ' Please re-try.');
                    });
            })
            .catch((error) => {
                page.error('Error while connecting: ' + error + ' Please re-try.');
            });
    }

    render() {
        const title = 'Connection';
        return (
            <main>
                <Helmet>
                    <title>{title} | Diplomacy</title>
                </Helmet>
                <Navigation title={title}/>
                <ConnectionForm onSubmit={this.onSubmit}/>
            </main>
        );
    }

    componentDidMount() {
        window.scrollTo(0, 0);
    }
}

ContentConnection.contextType = PageContext;
