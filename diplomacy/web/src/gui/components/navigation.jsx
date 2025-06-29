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
import Octicon, {Person} from "@primer/octicons-react";
import PropTypes from "prop-types";

export class Navigation extends React.Component {
    render() {
        const hasNavigation = this.props.navigation && this.props.navigation.length;
        if (hasNavigation) {
            return (
                <div className={'title row'}>
                    <div className={'col align-self-center'}>
                        <strong>{this.props.title}</strong>
                        {this.props.afterTitle ? this.props.afterTitle : ''}
                    </div>
                    <div className={'col-sm-1'}>
                        {(!hasNavigation && (
                            <div className={'float-right'}>
                                <strong>
                                    <u className={'mr-2'}>{this.props.username}</u>
                                    <Octicon icon={Person}/>
                                </strong>
                            </div>
                        )) || (
                            <div className="dropdown float-right">
                                <button className="btn btn-secondary dropdown-toggle" type="button"
                                        id="dropdownMenuButton" data-toggle="dropdown"
                                        aria-haspopup="true" aria-expanded="false">
                                    {(this.props.username && (
                                        <span>
                                                <u className={'mr-2'}>{this.props.username}</u>
                                                <Octicon icon={Person}/>
                                            </span>
                                    )) || 'Menu'}
                                </button>
                                <div className="dropdown-menu dropdown-menu-right"
                                     aria-labelledby="dropdownMenuButton">
                                    {this.props.navigation.map((nav, index) => {
                                        const navTitle = nav[0];
                                        const navAction = nav[1];
                                        return <span key={index} className="dropdown-item"
                                                     onClick={navAction}>{navTitle}</span>;
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            );
        }
        return (
            <div className={'title'}><strong>{this.props.title}</strong></div>
        );
    }
}

Navigation.propTypes = {
    title: PropTypes.string.isRequired,
    afterTitle: PropTypes.object,
    navigation: PropTypes.array,
    username: PropTypes.string,
};
