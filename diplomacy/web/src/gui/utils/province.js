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
const ProvinceType = {
    WATER: 'WATER',
    COAST: 'COAST',
    PORT: 'PORT',
    LAND: 'LAND'
};

export class Province {
    constructor(name, type, isSupplyCenter) {
        this.name = name;
        this.type = type;
        this.coasts = {};
        this.parent = null;
        this.neighbors = {};
        this.isSupplyCenter = isSupplyCenter;
        this.controller = null; // null or power name.
        this.controlType = null; // null, C (center), I (influence) or U (unit).
        this.unit = null; // null, A or F
        this.retreatController = null;
        this.retreatUnit = null; // null or `{unit type} {loc}`
        this.aliases = [];
    }

    compareControlType(a, b) {
        const controlTypeLevels = {C: 0, I: 1, U: 2};
        return controlTypeLevels[a] - controlTypeLevels[b];
    }

    __set_controller(controller, controlType) {
        this.controller = controller;
        this.controlType = controlType;
        for (let coast of Object.values(this.coasts))
            coast.setController(controller, controlType);
    }

    setController(controller, controlType) {
        if (!['C', 'I', 'U'].includes(controlType))
            throw new Error(`Invalid province control type (${controlType}), expected 'C', 'I' or 'U'.`);
        if (this.controller && this.controller !== controller) {
            const controlTypeComparison = this.compareControlType(controlType, this.controlType);
            if (controlTypeComparison === 0)
                throw new Error(`Found 2 powers (${this.controller}, ${controller}) trying to control same province ` +
                    `(${this.name}) with same control type (${controlType} VS ${this.controlType}).`);
            if (controlTypeComparison > 0)
                this.__set_controller(controller, controlType);
        } else
            this.__set_controller(controller, controlType);
    }

    setCoasts(provinces) {
        const name = this.name.toUpperCase();
        for (let entry of Object.entries(provinces)) {
            const pieces = entry[0].split(/[^A-Za-z0-9]+/);
            if (pieces.length > 1 && pieces[0].toUpperCase() === name) {
                this.coasts[entry[0]] = entry[1];
                entry[1].parent = this;
            }
        }
    }

    setNeighbors(neighborProvinces) {
        for (let province of neighborProvinces)
            this.neighbors[province.name] = province;
    }

    getLocationNames() {
        const arr = Object.keys(this.coasts);
        arr.splice(0, 0, this.name);
        return arr;
    }

    getOccupied(powerName) {
        if (!this.controller)
            return null;
        if (powerName && this.controller !== powerName)
            return null;
        if (this.unit)
            return this;
        for (let coast of Object.values(this.coasts))
            if (coast.unit)
                return coast;
        return null;
    }

    getRetreated(powerName) {
        if (this.retreatController === powerName)
            return this;
        for (let coast of Object.values(this.coasts))
            if (coast.retreatController === powerName)
                return coast;
        return null;
    }

    isCoast() {
        return this.type === ProvinceType.COAST;
    }

    isWater() {
        return this.type === ProvinceType.WATER;
    }

    _id(id) {
        return `_${id.toLowerCase()}`;
    }

    getID(identifiers) {
        let id = this._id(this.name);
        if (!identifiers[id]) {
            for (let alias of this.aliases) {
                id = this._id(alias);
                if (identifiers[id])
                    break;
            }
        }
        if (!identifiers[id] && this.isCoast())
            id = this.parent.getID(identifiers);
        return id;
    }
}
