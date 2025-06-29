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
import {Action} from "./action";
import PropTypes from 'prop-types';

export class Tabs extends React.Component {
    /** PROPERTIES
     * active: index of active menu (must be > menu.length).
     * highlights: dictionary mapping a menu indice to a highlight message
     * onChange: callback(index): receive index of menu to display.
     * **/

    generateTabAction(tabTitle, tabId, isActive, onChange, highlight) {
        return <Action isActive={isActive}
                       title={tabTitle}
                       onClick={() => onChange(tabId)}
                       highlight={highlight}
                       key={tabId}/>;
    }

    render() {
        if (!this.props.menu.length)
            throw new Error(`No tab menu given.`);
        if (this.props.menu.length !== this.props.titles.length)
            throw new Error(`Menu length (${this.props.menu.length}) != titles length (${this.props.titles.length})`);
        if (this.props.active && !this.props.menu.includes(this.props.active))
            throw new Error(`Invalid active tab name, got ${this.props.active}, expected one of: ${this.props.menu.join(', ')}`);
        const active = this.props.active || this.props.menu[0];
        return (
            <div className={'tabs mb-3'}>
                <nav className={'tabs-bar nav nav-tabs justify-content-center mb-3'}>
                    {this.props.menu.map((tabName, index) => this.generateTabAction(
                        this.props.titles[index], tabName, active === tabName, this.props.onChange,
                        (this.props.highlights.hasOwnProperty(tabName) && this.props.highlights[tabName]) || null
                    ))}
                </nav>
                {this.props.children}
            </div>
        );
    }
}

Tabs.propTypes = {
    menu: PropTypes.arrayOf(PropTypes.string).isRequired, // tab names
    titles: PropTypes.arrayOf(PropTypes.string).isRequired, // tab titles
    onChange: PropTypes.func.isRequired, // callback(tab name)
    children: PropTypes.array.isRequired,
    active: PropTypes.string, // current active tab name
    highlights: PropTypes.object, // {tab name => highligh message (optional)}
};

Tabs.defaultProps = {
    highlights: {}
};
