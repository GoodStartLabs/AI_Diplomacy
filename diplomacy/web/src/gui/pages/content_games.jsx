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
import {Tabs} from "../components/tabs";
import {Table} from "../components/table";
import {FindForm} from "../forms/find_form";
import {InlineGameView} from "../utils/inline_game_view";
import {Helmet} from "react-helmet";
import {Navigation} from "../components/navigation";
import {PageContext} from "../components/page_context";
import {ContentGame} from "./content_game";
import PropTypes from 'prop-types';
import {Tab} from "../components/tab";
import {GameCreationWizard} from "../wizards/gameCreation/gameCreationWizard";

const TABLE_LOCAL_GAMES = {
    game_id: ['Game ID', 0],
    deadline: ['Deadline', 1],
    rights: ['Rights', 2],
    rules: ['Rules', 3],
    players: ['Players/Expected', 4],
    status: ['Status', 5],
    phase: ['Phase', 6],
    join: ['Join', 7],
    actions: ['Actions', 8],
};

export class ContentGames extends React.Component {

    constructor(props) {
        super(props);
        this.state = {tab: null};
        this.changeTab = this.changeTab.bind(this);
        this.onFind = this.onFind.bind(this);
        this.onCreate = this.onCreate.bind(this);
        this.wrapGameData = this.wrapGameData.bind(this);
    }

    getPage() {
        return this.context;
    }

    onFind(form) {
        for (let field of ['game_id', 'status', 'include_protected', 'for_omniscience'])
            if (!form[field])
                form[field] = null;
        this.getPage().channel.listGames(form)
            .then((data) => {
                this.getPage().success('Found ' + data.length + ' data.');
                this.getPage().addGamesFound(data);
                this.getPage().loadGames();
            })
            .catch((error) => {
                this.getPage().error('Error when looking for distant games: ' + error);
            });
    }

    onCreate(form) {
        let networkGame = null;
        this.getPage().channel.createGame(form)
            .then((game) => {
                this.getPage().addToMyGames(game.local);
                networkGame = game;
                return networkGame.getAllPossibleOrders();
            })
            .then(allPossibleOrders => {
                networkGame.local.setPossibleOrders(allPossibleOrders);
                this.getPage().load(
                    `game: ${networkGame.local.game_id}`,
                    <ContentGame data={networkGame.local}/>,
                    {success: 'Game created.'}
                );
            })
            .catch((error) => {
                this.getPage().error('Error when creating a game: ' + error);
            });
    }

    changeTab(tabIndex) {
        this.setState({tab: tabIndex});
    }

    wrapGameData(gameData) {
        return new InlineGameView(this.getPage(), gameData, this.getPage().availableMaps);
    }

    gameCreationButton() {
        return (
            <button type="button"
                    className="btn btn-danger btn-sm mx-0 mx-sm-4"
                    onClick={() => this.getPage().dialog(onClose => (
                        <GameCreationWizard availableMaps={this.getPage().availableMaps}
                                            onCancel={onClose}
                                            username={this.getPage().channel.username}
                                            onSubmit={(form) => {
                                                onClose();
                                                this.onCreate(form);
                                            }}/>
                    ))}>
                <strong>create a game</strong>
            </button>
        );
    }

    render() {
        const title = 'Games';
        const page = this.getPage();
        const navigation = [
            ['load a game from disk', page.loadGameFromDisk],
            ['logout', page.logout]
        ];
        const myGames = this.props.myGames;
        const gamesFound = this.props.gamesFound;
        myGames.sort((a, b) => b.timestamp_created - a.timestamp_created);
        gamesFound.sort((a, b) => b.timestamp_created - a.timestamp_created);
        const tab = this.state.tab ? this.state.tab : (myGames.length ? 'my-games' : 'find');
        return (
            <main>
                <Helmet>
                    <title>{title} | Diplomacy</title>
                </Helmet>
                <Navigation title={title} afterTitle={this.gameCreationButton()}
                            username={page.channel.username} navigation={navigation}/>
                <Tabs menu={['find', 'my-games']} titles={['Find', 'My Games']}
                      onChange={this.changeTab} active={tab}>
                    {tab === 'find' ? (
                        <Tab id="tab-games-find" display={true}>
                            <FindForm onSubmit={this.onFind}/>
                            <Table className={"table table-striped"} caption={"Games"} columns={TABLE_LOCAL_GAMES}
                                   data={gamesFound} wrapper={this.wrapGameData}/>
                        </Tab>
                    ) : ''}
                    {tab === 'my-games' ? (
                        <Tab id={'tab-my-games'} display={true}>
                            <Table className={"table table-striped"} caption={"My games"} columns={TABLE_LOCAL_GAMES}
                                   data={myGames} wrapper={this.wrapGameData}/>
                        </Tab>
                    ) : ''}
                </Tabs>
            </main>
        );
    }

    componentDidMount() {
        window.scrollTo(0, 0);
    }
}

ContentGames.contextType = PageContext;
ContentGames.propTypes = {
    gamesFound: PropTypes.array.isRequired,
    myGames: PropTypes.array.isRequired
};
