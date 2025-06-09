// diplomacy/integration/webdiplomacy_net/tests/game.spec.ts

import {
    turn_to_phase,
    unit_dict_to_strings, // Renamed from unit_dict_to_str for clarity (plural strings)
    center_dict_to_strings, // Renamed from center_dict_to_str
    order_dict_to_strings, // Renamed from order_dict_to_str
    WebDiplomacyUnitDict,
    WebDiplomacyCenterDict,
    WebDiplomacyOrderDict,
} from '../game'; // Adjust path as necessary
import { CACHE } from '../utils'; // To ensure cache is initialized for tests

// Initialize map data for tests if not already done by utils import
// This is implicitly handled by importing utils.ts as it populates CACHE on load.

describe('turn_to_phase', () => {
    it('should test S1901M', () => {
        const phase = turn_to_phase(0, 'Diplomacy');
        expect(phase).toBe('S1901M');
    });
    it('should test S1901R', () => {
        const phase = turn_to_phase(0, 'Retreats');
        expect(phase).toBe('S1901R');
    });
    it('should test F1901M', () => {
        const phase = turn_to_phase(1, 'Diplomacy');
        expect(phase).toBe('F1901M');
    });
    it('should test F1901R', () => {
        const phase = turn_to_phase(1, 'Retreats');
        expect(phase).toBe('F1901R');
    });
    it('should test W1901A', () => {
        const phase = turn_to_phase(1, 'Builds', 1901); // Assuming default first year or pass explicitly
        expect(phase).toBe('W1901A');
    });
    it('should test S1902M', () => {
        const phase = turn_to_phase(2, 'Diplomacy');
        expect(phase).toBe('S1902M');
    });
});

describe('unit_dict_to_strings', () => {
    it('should parse Army France', () => {
        const unit_dict: WebDiplomacyUnitDict = { unitType: 'Army', terrID: 47, countryID: 2, retreating: 'No' };
        const [powerName, unit] = unit_dict_to_strings(unit_dict, 1); // map_id 1 for standard
        expect(powerName).toBe('FRANCE');
        expect(unit).toBe('A PAR');
    });
    it('should parse Dislodged Fleet England', () => {
        const unit_dict: WebDiplomacyUnitDict = { unitType: 'Fleet', terrID: 6, countryID: 1, retreating: 'Yes' };
        const [powerName, unit] = unit_dict_to_strings(unit_dict, 1);
        expect(powerName).toBe('ENGLAND');
        expect(unit).toBe('*F LON');
    });
    it('should handle invalid unit', () => {
        const unit_dict: WebDiplomacyUnitDict = { unitType: 'Fleet', terrID: 99, countryID: 0, retreating: 'No' }; // terrID 99 is invalid for standard
        const [powerName, unit] = unit_dict_to_strings(unit_dict, 1);
        expect(powerName).toBeNull(); // Or specific error handling if preferred
        expect(unit).toBeNull();
    });
});

describe('center_dict_to_strings', () => {
    it('should parse centers', () => {
        let [powerName, center] = center_dict_to_strings({ countryID: 1, terrID: 6 } as WebDiplomacyCenterDict, 1);
        expect(powerName).toBe('ENGLAND');
        expect(center).toBe('LON');

        [powerName, center] = center_dict_to_strings({ countryID: 2, terrID: 47 } as WebDiplomacyCenterDict, 1);
        expect(powerName).toBe('FRANCE');
        expect(center).toBe('PAR');
    });
});

describe('order_dict_to_strings', () => {
    // mapName 'standard' corresponds to map_id 1
    const mapName = 'standard';
    const mapId = 1;

    it('should parse S1901M Hold', () => {
        const order_dict: WebDiplomacyOrderDict = {
            countryID: 2, // FRANCE
            terrID: 6,    // LON
            unitType: 'Army',
            type: 'Hold',
        };
        const [powerName, order] = order_dict_to_strings(order_dict, 'Diplomacy', mapId, mapName);
        expect(powerName).toBe('FRANCE');
        expect(order).toBe('A LON H');
    });

    it('should parse S1901R Disband', () => {
        const order_dict: WebDiplomacyOrderDict = {
            countryID: 1, // ENGLAND
            terrID: 6,    // LON
            unitType: 'Fleet',
            type: 'Disband',
        };
        const [powerName, order] = order_dict_to_strings(order_dict, 'Retreats', mapId, mapName);
        expect(powerName).toBe('ENGLAND');
        expect(order).toBe('F LON D');
    });

    it('should parse F1901M Move', () => {
        const order_dict: WebDiplomacyOrderDict = {
            countryID: 2, // FRANCE
            terrID: 6,    // LON
            unitType: 'Army',
            type: 'Move',
            toTerrID: 47, // PAR
            viaConvoy: 'Yes',
        };
        const [powerName, order] = order_dict_to_strings(order_dict, 'Diplomacy', mapId, mapName);
        expect(powerName).toBe('FRANCE');
        expect(order).toBe('A LON - PAR VIA');
    });

    it('should parse F1901R Retreat', () => {
        const order_dict: WebDiplomacyOrderDict = {
            countryID: 3, // ITALY
            terrID: 6,    // LON
            unitType: 'Army',
            type: 'Retreat',
            toTerrID: 47, // PAR
        };
        const [powerName, order] = order_dict_to_strings(order_dict, 'Retreats', mapId, mapName);
        expect(powerName).toBe('ITALY');
        expect(order).toBe('A LON R PAR');
    });

    it('should parse W1901A Build Army', () => {
        const order_dict: WebDiplomacyOrderDict = {
            countryID: 2, // FRANCE
            // terrID is null for builds in some API versions, toTerrID is used
            terrID: 6, // LON - Python test used terrID, let's assume it can be primary loc for unit
            unitType: 'Army', // This might be inferred from "Build Army"
            type: 'Build Army',
            toTerrID: 6, // LON
        };
        const [powerName, order] = order_dict_to_strings(order_dict, 'Builds', mapId, mapName);
        expect(powerName).toBe('FRANCE');
        expect(order).toBe('A LON B');
    });

    it('should parse W1901A Build Fleet', () => {
        const order_dict: WebDiplomacyOrderDict = {
            countryID: 1, // ENGLAND
            terrID: 6,    // LON
            type: 'Build Fleet',
            toTerrID: 6, // LON (location of build)
        };
        const [powerName, order] = order_dict_to_strings(order_dict, 'Builds', mapId, mapName);
        expect(powerName).toBe('ENGLAND');
        expect(order).toBe('F LON B');
    });


    it('should parse S1902M Hold', () => {
        const order_dict: WebDiplomacyOrderDict = {
            countryID: 2, // FRANCE
            terrID: 6,    // LON
            unitType: 'Army',
            type: 'Hold',
        };
        const [powerName, order] = order_dict_to_strings(order_dict, 'Diplomacy', mapId, mapName);
        expect(powerName).toBe('FRANCE');
        expect(order).toBe('A LON H');
    });
});
