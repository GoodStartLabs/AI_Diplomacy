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
import {JoinForm} from "../forms/join_form";
import {STRINGS} from "../../diplomacy/utils/strings";
import {ContentGame} from "../pages/content_game";
import {Button} from "../components/button";
import {DeleteButton} from "../components/delete_button";

export class InlineGameView {
    constructor(page, gameData, maps) {
        this.page = page;
        this.game = gameData;
        this.maps = maps;
        this.get = this.get.bind(this);
        this.joinGame = this.joinGame.bind(this);
        this.showGame = this.showGame.bind(this);
    }

    joinGame(formData) {
        const form = {
            power_name: formData[`power_name_${this.game.game_id}`],
            registration_password: formData[`registration_password_${this.game.game_id}`]
        };
        if (!form.power_name)
            form.power_name = null;
        if (!form.registration_password)
            form.registration_password = null;
        form.game_id = this.game.game_id;
        this.page.channel.joinGame(form)
            .then((networkGame) => {
                this.game = networkGame.local;
                this.page.addToMyGames(this.game);
                return networkGame.getAllPossibleOrders();
            })
            .then(allPossibleOrders => {
                this.game.setPossibleOrders(allPossibleOrders);
                this.page.load(
                    `game: ${this.game.game_id}`,
                    <ContentGame data={this.game}/>,
                    {success: 'Game joined.'}
                );
            })
            .catch((error) => {
                this.page.error('Error when joining game ' + this.game.game_id + ': ' + error);
            });
    }

    showGame() {
        this.page.load(`game: ${this.game.game_id}`, <ContentGame data={this.game}/>);
    }

    getJoinUI() {
        if (this.game.role) {
            // Game already joined.
            return (
                <div className={'games-form'}>
                    <Button key={'button-show-' + this.game.game_id} title={'show'} onClick={this.showGame}/>
                    <Button key={'button-leave-' + this.game.game_id} title={'leave'}
                            onClick={() => this.page.leaveGame(this.game.game_id)}/>
                </div>
            );
        } else {
            // Game not yet joined.
            return <JoinForm key={this.game.game_id}
                             game_id={this.game.game_id}
                             powers={this.game.controlled_powers}
                             availablePowers={this.maps[this.game.map_name].powers}
                             password_required={this.game.registration_password}
                             onSubmit={this.joinGame}/>;
        }
    }

    getActionButtons() {
        const buttons = [];
        // Button to add/remove game from "My games" list.
        if (this.page.hasMyGame(this.game.game_id)) {
            if (!this.game.client) {
                // Game in My Games and not joined. We can remove it.
                buttons.push(<Button key={`my-game-remove`} title={'Remove from My Games'}
                                     small={true} large={true}
                                     onClick={() => this.page.removeFromMyGames(this.game.game_id)}/>);
            }
        } else {
            // Game not in My Games, we can add it.
            buttons.push(<Button key={`my-game-add`} title={'Add to My Games'}
                                 small={true} large={true}
                                 onClick={() => this.page.addToMyGames(this.game)}/>);
        }
        // Button to delete game.
        if ([STRINGS.MASTER_TYPE, STRINGS.OMNISCIENT_TYPE].includes(this.game.observer_level)) {
            buttons.push(
                <DeleteButton key={`game-delete-${this.game.game_id}`}
                              title={'Delete this game'}
                              confirmTitle={'Click again to confirm deletion'}
                              waitingTitle={'Deleting ...'}
                              onClick={() => this.page.removeGame(this.game.game_id)}/>
            );
        }
        return buttons;
    }

    get(name) {
        if (name === 'players') {
            return `${this.game.n_players} / ${this.game.n_controls}`;
        }
        if (name === 'rights') {
            const elements = [];
            if (this.game.observer_level) {
                let levelName = '';
                if (this.game.observer_level === STRINGS.MASTER_TYPE)
                    levelName = 'master';
                else if (this.game.observer_level === STRINGS.OMNISCIENT_TYPE)
                    levelName = 'omniscient';
                else
                    levelName = 'observer';
                elements.push((<p key={0}><strong>Observer right:</strong><br/>{levelName}</p>));
            }
            if (this.game.controlled_powers && this.game.controlled_powers.length) {
                const powers = this.game.controlled_powers.slice();
                powers.sort();
                elements.push((
                    <div key={1}><strong>Currently handled power{powers.length === 1 ? '' : 's'}</strong></div>));
                for (let power of powers)
                    elements.push((<div key={power}>{power}</div>));
            }
            return elements.length ? (<div>{elements}</div>) : '';
        }
        if (name === 'rules') {
            if (this.game.rules)
                return <div>{this.game.rules.map(rule => <div key={rule}>{rule}</div>)}</div>;
            return '';
        }
        if (name === 'join')
            return this.getJoinUI();
        if (name === 'actions')
            return this.getActionButtons();
        if (name === 'game_id') {
            const date = new Date(this.game.timestamp_created / 1000);
            const dateString = `${date.toLocaleDateString()} - ${date.toLocaleTimeString()}`;
            return <div>
                <div><strong>{this.game.game_id}</strong></div>
                <div>({dateString})</div>
                <div><em>{this.game.map_name}</em></div>
            </div>;
        }
        return this.game[name];
    }
}
