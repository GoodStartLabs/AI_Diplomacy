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
class VariantInfo {
    constructor(variantName, variantTitle) {
        this.name = variantName;
        this.title = variantTitle;
        this.map = null;
    }

    svgName() {
        return this.map.name;
    }
}

class MapInfo {
    constructor(mapName, mapTitle, variants) {
        this.name = mapName;
        this.title = mapTitle;
        this.variants = null;
        if (variants) {
            this.variants = [];
            for (let variant of variants) {
                variant.map = this;
                this.variants.push(variant);
            }
        }
    }

    svgName() {
        return this.name;
    }
}

export const Maps = [
    new MapInfo('standard', 'Standard', [
        new VariantInfo('standard', 'Default'),
        new VariantInfo('standard_age_of_empires', 'Age of empires'),
        new VariantInfo('standard_age_of_empires_2', 'Age of empires II'),
        new VariantInfo('standard_fleet_rome', 'Fleet at Rome'),
        new VariantInfo('standard_france_austria', 'France VS Austria'),
        new VariantInfo('standard_germany_italy', 'Germany VS Italy')
    ]),
    new MapInfo('ancmed', 'Ancient Mediterranean', [
        new VariantInfo('ancmed', 'Default'),
        new VariantInfo('ancmed_age_of_empires', 'Age of empires')
    ]),
    new MapInfo('modern', 'Modern'),
    new MapInfo('pure', 'Pure'),
];
