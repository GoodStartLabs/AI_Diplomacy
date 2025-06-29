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
import {Button} from "./button";

export class PowerOrders extends React.Component {
    render() {
        const orderEntries = this.props.orders ? Object.entries(this.props.orders) : null;
        let display = null;
        if (orderEntries) {
            if (orderEntries.length) {
                orderEntries.sort((a, b) => a[1].order.localeCompare(b[1].order));
                display = (
                    <div className={'container order-list'}>
                        {orderEntries.map((entry, index) => (
                            <div
                                className={`row order-entry entry-${1 + index % 2} ` + (entry[1].local ? 'local' : 'server')}
                                key={index}>
                                <div className={'col align-self-center order'}>
                                    <span className={'order-string'}>{entry[1].order}</span>
                                    {entry[1].local ? '' : <span className={'order-mark'}> [S]</span>}
                                </div>
                                <div className={'col remove-button'}>
                                    <Button title={'-'} onClick={() => this.props.onRemove(this.props.name, entry[1])}/>
                                </div>
                            </div>
                        ))}
                    </div>
                );
            } else if (this.props.serverCount === 0) {
                display = (<div className={'empty-orders'}>Empty orders set</div>);
            } else {
                display = (<div className={'empty-orders'}>Local empty orders set</div>);
            }
        } else {
            if (this.props.serverCount < 0) {
                display = <div className={'no-orders'}>No orders!</div>;
            } else {
                display = <div className={'empty-orders'}>Asking to unset orders</div>;
            }
        }
        return (
            <div className={'power-orders'}>
                <div className={'title'}>
                    <span className={'name'}>{this.props.name}</span>
                    <span className={this.props.wait ? 'wait' : 'no-wait'}>
                        {(this.props.wait ? ' ' : ' not') + ' waiting'}
                    </span>
                </div>
                {display}
            </div>
        );
    }
}

PowerOrders.propTypes = {
    wait: PropTypes.bool,
    name: PropTypes.string,
    orders: PropTypes.object,
    serverCount: PropTypes.number,
    onRemove: PropTypes.func,
};
