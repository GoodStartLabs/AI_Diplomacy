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
import {STRINGS} from "../../diplomacy/utils/strings";
import React from "react";

function getName(power) {
    if (power.isEliminated())
        return <span className="dummy"><em><s>{power.name.toLowerCase()}</s> (eliminated)</em></span>;
    return power.name;
}

function getController(power) {
    if (power.isEliminated())
        return <span className="dummy"><em>N/A</em></span>;
    const controller = power.getController();
    return <span className={controller === STRINGS.DUMMY ? 'dummy' : 'controller'}>{controller}</span>;
}

function getOrderFlag(power) {
    if (power.isEliminated() || power.game.orderableLocations[power.name].length === 0)
        return <span className="dummy"><em>N/A</em></span>;
    const value = ['no', 'empty', 'yes'][power.order_is_set];
    return <span className={value}>{value}</span>;
}

function getWaitFlag(power) {
    if (power.isEliminated())
        return <span className="dummy"><em>N/A</em></span>;
    return <span className={power.wait ? 'wait' : 'no-wait'}>{power.wait ? 'yes' : 'no'}</span>;
}

const GETTERS = {
    name: getName,
    controller: getController,
    order_is_set: getOrderFlag,
    wait: getWaitFlag
};

export class PowerView {
    constructor(power) {
        this.power = power;
    }

    static wrap(power) {
        return new PowerView(power);
    }

    get(key) {
        return GETTERS[key](this.power);
    }
}
