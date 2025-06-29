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
import {Province} from "./province";

export class MapData {
    constructor(mapInfo, game) {
        // mapInfo: {powers: [], supply_centers: [], aliases: {alias: name}, loc_type: {loc => type}, loc_abut: {loc => [abuts]}}
        // game: a NetworkGame object.
        this.game = game;
        this.powers = new Set(mapInfo.powers);
        this.supplyCenters = new Set(mapInfo.supply_centers);
        this.aliases = Object.assign({}, mapInfo.aliases);
        this.provinces = {};
        for (let entry of Object.entries(mapInfo.loc_type)) {
            const provinceName = entry[0];
            const provinceType = entry[1];
            this.provinces[provinceName] = new Province(provinceName, provinceType, this.supplyCenters.has(provinceName));
        }
        for (let entry of Object.entries(mapInfo.loc_abut)) {
            this.getProvince(entry[0]).setNeighbors(entry[1].map(name => this.getProvince(name)));
        }
        for (let province of Object.values(this.provinces)) {
            province.setCoasts(this.provinces);
        }
        for (let power of Object.values(this.game.powers)) {
            for (let center of power.centers) {
                this.getProvince(center).setController(power.name, 'C');
            }
            for (let loc of power.influence) {
                this.getProvince(loc).setController(power.name, 'I');
            }
            for (let unit of power.units) {
                this.__add_unit(unit, power.name);
            }
            for (let unit of Object.keys(power.retreats)) {
                this.__add_retreat(unit, power.name);
            }
        }
        for (let entry of Object.entries(this.aliases)) {
            const alias = entry[0];
            const provinceName = entry[1];
            const province = this.getProvince(provinceName);
            if (province)
                province.aliases.push(alias);
        }
    }

    __add_unit(unit, power_name) {
        const splitUnit = unit.split(/ +/);
        const unitType = splitUnit[0];
        const location = splitUnit[1];
        const province = this.getProvince(location);
        province.setController(power_name, 'U');
        province.unit = unitType;
    }

    __add_retreat(unit, power_name) {
        const splitUnit = unit.split(/ +/);
        const location = splitUnit[1];
        const province = this.getProvince(location);
        province.retreatController = power_name;
        province.retreatUnit = unit;
    }

    getProvince(abbr) {
        if (abbr === '')
            return null;
        if (abbr[0] === '_')
            abbr = abbr.substr(1, 3);
        if (!abbr)
            return null;
        if (this.provinces.hasOwnProperty(abbr))
            return this.provinces[abbr];
        if (this.provinces.hasOwnProperty(abbr.toUpperCase()))
            return this.provinces[abbr.toUpperCase()];
        if (this.provinces.hasOwnProperty(abbr.toLowerCase()))
            return this.provinces[abbr.toLowerCase()];
        if (this.aliases.hasOwnProperty(abbr))
            return this.provinces[this.aliases[abbr]];
        if (this.aliases.hasOwnProperty(abbr.toUpperCase()))
            return this.provinces[this.aliases[abbr.toUpperCase()]];
        if (this.aliases.hasOwnProperty(abbr.toLowerCase()))
            return this.provinces[this.aliases[abbr.toLowerCase()]];
        return null;
    }
}
