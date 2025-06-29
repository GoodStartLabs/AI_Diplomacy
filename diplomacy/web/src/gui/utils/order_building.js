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
/*eslint no-unused-vars: ["error", { "args": "none" }]*/

function assertLength(expected, given) {
    if (expected !== given)
        throw new Error(`Length error: expected ${expected}, given ${given}.`);
}

export class ProvinceCheck {

    static retreated(province, powerName) {
        const retreatProvince = province.getRetreated(powerName);
        if (!retreatProvince)
            throw new Error(`No retreated location at province ${province.name}.`);
        // No confusion possible, we select the only occupied location at this province.
        return [retreatProvince.retreatUnit];
    }

    static present(province, powerName) {
        let unit = null;
        let presenceProvince = province.getOccupied(powerName);
        if (presenceProvince) {
            unit = `${presenceProvince.unit} ${presenceProvince.name}`;
        } else {
            presenceProvince = province.getRetreated(powerName);
            if (!presenceProvince)
                throw new Error(`No unit or retreat at province ${province.name}.`);
            unit = presenceProvince.retreatUnit;
        }
        return [unit];
    }

    static occupied(province, powerName) {
        const occupiedProvince = province.getOccupied(powerName);
        if (!occupiedProvince)
            throw new Error(`No occupied location at province ${province.name}.`);
        // No confusion possible, we select the only occupied location at this province.
        const unit = occupiedProvince.unit;
        const name = occupiedProvince.name.toUpperCase();
        return [`${unit} ${name}`];
    }

    static occupiedByAny(province, unusedPowerName) {
        return ProvinceCheck.occupied(province, null);
    }

    static any(province, unusedPowerName) {
        // There may be many locations available for a province (e.g. many coasts).
        return province.getLocationNames();
    }

    static buildOrder(path) {
        switch (path[0]) {
            case 'H':
                return ProvinceCheck.holdToString(path);
            case 'M':
                return ProvinceCheck.moveToString(path);
            case 'V':
                return ProvinceCheck.moveViaToString(path);
            case 'S':
                return ProvinceCheck.supportToString(path);
            case 'C':
                return ProvinceCheck.convoyToString(path);
            case 'R':
                return ProvinceCheck.retreatToString(path);
            case 'D':
                return ProvinceCheck.disbandToString(path);
            case 'A':
                return ProvinceCheck.buildArmyToString(path);
            case 'F':
                return ProvinceCheck.buildFleetToString(path);
            default:
                throw new Error('Unable to build order from path ' + JSON.stringify(path));
        }
    }

    static holdToString(path) {
        assertLength(2, path.length);
        return `${path[1]} ${path[0]}`;
    }

    static moveToString(path) {
        assertLength(3, path.length);
        return `${path[1]} - ${path[2]}`;
    }

    static moveViaToString(path) {
        return ProvinceCheck.moveToString(path) + ' VIA';
    }

    static supportToString(path) {
        assertLength(4, path.length);
        let order = `${path[1]} ${path[0]} ${path[2]}`;
        if (path[2].substr(2) !== path[3])
            order += ` - ${path[3]}`;
        return order;
    }

    static convoyToString(path) {
        assertLength(4, path.length);
        return `${path[1]} ${path[0]} ${path[2]} - ${path[3]}`;
    }

    static retreatToString(path) {
        assertLength(3, path.length);
        return `${path[1]} ${path[0]} ${path[2]}`;
    }

    static disbandToString(path) {
        assertLength(2, path.length);
        return `${path[1]} ${path[0]}`;
    }

    static buildArmyToString(path) {
        assertLength(2, path.length);
        return `${path[0]} ${path[1]} B`;
    }

    static buildFleetToString(path) {
        assertLength(2, path.length);
        return `${path[0]} ${path[1]} B`;
    }

}

export const ORDER_BUILDER = {
    H: {
        name: 'hold (H)',
        steps: [ProvinceCheck.occupied]
    },
    M: {
        name: 'move (M)',
        steps: [ProvinceCheck.occupied, ProvinceCheck.any]
    },
    V: {
        name: 'move VIA (V)',
        steps: [ProvinceCheck.occupied, ProvinceCheck.any]
    },
    S: {
        name: 'support (S)',
        steps: [ProvinceCheck.occupied, ProvinceCheck.occupiedByAny, ProvinceCheck.any]
    },
    C: {
        name: 'convoy (C)',
        steps: [ProvinceCheck.occupied, ProvinceCheck.occupiedByAny, ProvinceCheck.any]
    },
    R: {
        name: 'retreat (R)',
        steps: [ProvinceCheck.retreated, ProvinceCheck.any]
    },
    D: {
        name: 'disband (D)',
        steps: [ProvinceCheck.present]
    },
    A: {
        name: 'build army (A)',
        steps: [ProvinceCheck.any]
    },
    F: {
        name: 'build fleet (F)',
        steps: [ProvinceCheck.any]
    },
};

export const POSSIBLE_ORDERS = {
    // Allowed orders for movement phase step.
    M: ['H', 'M', 'V', 'S', 'C'],
    // Allowed orders for retreat phase step.
    R: ['R', 'D'],
    // Allowed orders for adjustment phase step.
    A: ['D', 'A', 'F'],
    sorting: {
        M: {M: 0, V: 1, S: 2, C: 3, H: 4},
        R: {R: 0, D: 1},
        A: {A: 0, F: 1, D: 2}
    },
    sortOrderTypes: function (arr, phaseType) {
        arr.sort((a, b) => POSSIBLE_ORDERS.sorting[phaseType][a] - POSSIBLE_ORDERS.sorting[phaseType][b]);
    }
};

export function extendOrderBuilding(powerName, orderType, currentOrderPath, location, onBuilding, onBuilt, onError) {
    const selectedPath = [orderType].concat(currentOrderPath, location);
    if (selectedPath.length - 1 < ORDER_BUILDER[orderType].steps.length) {
        // Checker OK, update.
        onBuilding(powerName, selectedPath);
    } else {
        try {
            // Order created.
            const orderString = ProvinceCheck.buildOrder(selectedPath);
            onBuilt(powerName, orderString);
        } catch (error) {
            onError(error.toString());
        }
    }
}
