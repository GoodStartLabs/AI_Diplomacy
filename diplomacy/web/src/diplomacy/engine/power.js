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
/** Class Power. **/
import {SortedDict} from "../utils/sorted_dict";
import {STRINGS} from "../utils/strings";

export class Power {
    constructor(name, role, game) {
        this.game = game;
        this.role = role;

        this.name = name;
        this.controller = new SortedDict();
        this.vote = null;
        this.order_is_set = 0;
        this.wait = !this.game.isRealTime();
        this.centers = [];
        this.homes = [];
        this.units = [];
        this.retreats = {};
        this.orders = [];
        this.influence = [];
    }

    isControlled() {
        if (this.controller && this.controller.size()) {
            return this.controller.lastValue() !== STRINGS.DUMMY;
        }
        return false;
    }

    getController() {
        return (this.controller && this.controller.lastValue()) || STRINGS.DUMMY;
    }

    isEliminated() {
        return !(this.units.length || this.centers.length || Object.keys(this.retreats).length);
    }

    setState(powerState) {
        this.name = powerState.name;
        this.controller = new SortedDict(powerState.controller);
        this.vote = powerState.vote;
        this.order_is_set = powerState.order_is_set;
        this.wait = powerState.wait;
        this.centers = powerState.centers;
        this.homes = powerState.homes;
        this.units = powerState.units;
        this.retreats = powerState.retreats;
        this.influence = powerState.influence || [];
        // Get orders.
        this.orders = [];
        if (this.game.phase.charAt(this.game.phase.length - 1) === 'M') {
            if (this.game.isNoCheck()) {
                for (let value of Object.values(powerState.orders)) if (value)
                    this.orders.push(value);
            } else {
                for (let unit of Object.keys(powerState.orders))
                    this.orders.push(unit + ' ' + powerState.orders[unit]);
            }
        } else {
            for (let order of powerState.adjust)
                if (order && order !== 'WAIVE' && !order.startsWith('VOID '))
                    this.orders.push(order);
        }
    }

    copy() {
        const power = new Power(this.name, this.role, this.game);
        for (let key of this.controller.keys())
            power.controller.put(key, this.controller.get(key));
        power.vote = this.vote;
        power.order_is_set = this.order_is_set;
        power.wait = this.wait;
        power.centers = this.centers.slice();
        power.homes = this.homes.slice();
        power.units = this.units.slice();
        power.retreats = Object.assign({}, this.retreats);
        power.influence = this.influence.slice();
        power.orders = this.orders.slice();
        return power;
    }

    updateController(controller, timestamp) {
        this.controller.put(timestamp, controller);
    }

    setOrders(orders) {
        this.orders = orders.slice();
        this.order_is_set = this.orders.length ? 2 : 1;
    }

    setDummy() {
        this.controller.clear();
    }

    clearCenters() {
        this.centers = [];
    }

    clearOrders() {
        this.orders = [];
        this.order_is_set = 0;
        this.wait = !this.game.isRealTime();
    }

    clearUnits() {
        this.units = [];
        this.influence = [];
    }

    getOrders() {
        return this.orders.slice();
    }
}
