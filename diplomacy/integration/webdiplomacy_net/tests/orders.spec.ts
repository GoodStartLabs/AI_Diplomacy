// diplomacy/integration/webdiplomacy_net/tests/orders.spec.ts

import { WebDiplomacyOrder } from '../orders';
import { WebDiplomacyOrderDict } from '../game'; // Assuming this is defined for the dict structure
// import { DiplomacyGame } from '../../../engine/game'; // May be needed if game context is used for convoy path tests
// import { DiplomacyMap } from '../../../engine/map';   // May be needed for map context

// Helper function to compare dictionaries, excluding 'convoyPath'
function compareOrderDicts(dict1: Partial<WebDiplomacyOrderDict>, dict2: Partial<WebDiplomacyOrderDict>): boolean {
    const keys1 = new Set(Object.keys(dict1).filter(k => k !== 'convoyPath'));
    const keys2 = new Set(Object.keys(dict2).filter(k => k !== 'convoyPath'));

    if (keys1.size !== keys2.size) return false;

    for (const key of Array.from(keys1)) {
        if (!keys2.has(key)) return false;
        if ((dict1 as any)[key] !== (dict2 as any)[key]) {
            // Allow for terrID/toTerrID/fromTerrID to be number or string due to API inconsistencies
            if (['terrID', 'toTerrID', 'fromTerrID'].includes(key)) {
                if (String((dict1 as any)[key]) !== String((dict2 as any)[key])) return false;
            } else {
                return false;
            }
        }
    }
    return true;
}

describe('WebDiplomacyOrder Construction and Conversion', () => {
    // Default map for these tests is 'standard' (map_id: 1)
    const defaultMapName = 'standard';
    const defaultMapId = 1;

    describe('Hold Orders', () => {
        it('should correctly parse and format "A PAR H"', () => {
            const raw_order = 'A PAR H';
            const expected_order_str = 'A PAR H';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 47, unitType: 'Army', type: 'Hold', toTerrID: '', fromTerrID: '', viaConvoy: ''
            };

            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);

            const orderFromDict = new WebDiplomacyOrder(expected_order_dict as WebDiplomacyOrderDict, defaultMapId);
            expect(orderFromDict.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromDict.to_dict(), expected_order_dict)).toBe(true);
        });

        it('should handle invalid location "A ABC H"', () => {
            const raw_order = 'A ABC H';
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(''); // Or handle error as per implementation
            expect(orderFromString.isValid()).toBe(false);
        });

        it('should correctly parse and format "F LON H"', () => {
            const raw_order = 'F LON H';
            const expected_order_str = 'F LON H';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 6, unitType: 'Fleet', type: 'Hold', toTerrID: '', fromTerrID: '', viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);

            const orderFromDict = new WebDiplomacyOrder(expected_order_dict as WebDiplomacyOrderDict, defaultMapId);
            expect(orderFromDict.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromDict.to_dict(), expected_order_dict)).toBe(true);
        });
    });

    describe('Move Orders', () => {
        it('should parse "A YOR - LON"', () => {
            const raw_order = 'A YOR - LON';
            const expected_order_str = 'A YOR - LON';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 4, unitType: 'Army', type: 'Move', toTerrID: 6, fromTerrID: '', viaConvoy: 'No'
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });

        it('should parse "A PAR - LON VIA"', () => {
            const raw_order = 'A PAR - LON VIA';
            const expected_order_str = 'A PAR - LON VIA'; // Assuming VIA is kept by to_string if present
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 47, unitType: 'Army', type: 'Move', toTerrID: 6, fromTerrID: '', viaConvoy: 'Yes'
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });

        it('should parse "F BRE - MAO"', () => {
            const raw_order = 'F BRE - MAO';
            const expected_order_str = 'F BRE - MAO';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 46, unitType: 'Fleet', type: 'Move', toTerrID: 61, fromTerrID: '', viaConvoy: 'No'
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });
    });

    describe('Support Hold Orders', () => {
        it('should parse "A PAR S F BRE"', () => {
            const raw_order = 'A PAR S F BRE';
            const expected_order_str = 'A PAR S BRE'; // Normalized string might remove supported unit type
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 47, unitType: 'Army', type: 'Support hold', toTerrID: 46, fromTerrID: '', viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(expected_order_str); // Or raw_order if to_string keeps unit type
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });
    });

    describe('Support Move Orders', () => {
        it('should parse "A PAR S F MAO - BRE"', () => {
            const raw_order = 'A PAR S F MAO - BRE';
            const expected_order_str = 'A PAR S MAO - BRE'; // Normalized string might remove unit type
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 47, unitType: 'Army', type: 'Support move', toTerrID: 46, fromTerrID: 61, viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });
    });

    describe('Convoy Orders', () => {
        it('should parse "F MAO C A PAR - LON"', () => {
            const raw_order = 'F MAO C A PAR - LON';
            const expected_order_str = 'F MAO C A PAR - LON'; // String form usually keeps convoyed unit type
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 61, unitType: 'Fleet', type: 'Convoy', toTerrID: 6, fromTerrID: 47, viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName);
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });
    });

    describe('Retreat Orders', () => {
        it('should parse "A PAR R LON"', () => {
            const raw_order = 'A PAR R LON';
            const expected_order_str = 'A PAR R LON';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 47, unitType: 'Army', type: 'Retreat', toTerrID: 6, fromTerrID: '', viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName, 'R');
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });

        it('should convert "A PAR - LON" to retreat in Retreat phase', () => {
            const raw_order = 'A PAR - LON';
            const expected_order_str = 'A PAR R LON';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 47, unitType: 'Army', type: 'Retreat', toTerrID: 6, fromTerrID: '', viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName, 'R');
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });
    });

    describe('Disband Orders', () => {
        it('should parse "A PAR D" in Retreat phase', () => {
            const raw_order = 'A PAR D';
            const expected_order_str = 'A PAR D';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 47, unitType: 'Army', type: 'Disband', toTerrID: '', fromTerrID: '', viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName, 'R');
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });

        it('should parse "F SPA/NC D" in Retreat phase (disband with coast)', () => {
            const raw_order = 'F SPA/NC D';
            const expected_order_str = 'F SPA/NC D';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 76, unitType: 'Fleet', type: 'Disband', toTerrID: '', fromTerrID: '', viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName, 'R');
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });

        it('should parse "F SPA/NC D" as "Destroy" in Adjustment phase (disband without coast for API)', () => {
            const raw_order = 'F SPA/NC D'; // User input might still include coast
            const expected_order_str = 'F SPA D'; // String output for adjustment disband is base province
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 8, unitType: 'Fleet', type: 'Destroy', toTerrID: 8, fromTerrID: '', viaConvoy: ''
            }; // terrID and toTerrID are base province ID for Destroy

            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName, 'A');
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);

            const orderFromDict = new WebDiplomacyOrder(expected_order_dict as WebDiplomacyOrderDict, defaultMapId, 'A');
             // Building from dict should yield the string representation that matches the dict's intent
            expect(orderFromDict.to_string()).toBe(expected_order_str); // F SPA D
            expect(compareOrderDicts(orderFromDict.to_dict(), expected_order_dict)).toBe(true);
        });
    });

    describe('Build Orders', () => {
        it('should parse "A PAR B"', () => {
            const raw_order = 'A PAR B';
            const expected_order_str = 'A PAR B';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 47, unitType: 'Army', type: 'Build Army', toTerrID: 47, fromTerrID: '', viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName, 'A');
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });
        it('should parse "F BRE B"', () => {
            const raw_order = 'F BRE B';
            const expected_order_str = 'F BRE B';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                terrID: 46, unitType: 'Fleet', type: 'Build Fleet', toTerrID: 46, fromTerrID: '', viaConvoy: ''
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName, 'A');
            expect(orderFromString.to_string()).toBe(expected_order_str);
            expect(compareOrderDicts(orderFromString.to_dict(), expected_order_dict)).toBe(true);
        });
    });

    describe('Waive Orders', () => {
        it('should parse "WAIVE"', () => {
            const raw_order = 'WAIVE';
            const expected_order_str = 'WAIVE';
            const expected_order_dict: Partial<WebDiplomacyOrderDict> = {
                 type: 'Wait', terrID: undefined, unitType: undefined, toTerrID: undefined, fromTerrID: undefined, viaConvoy: undefined
            };
            const orderFromString = new WebDiplomacyOrder(raw_order, defaultMapName, 'A');
            expect(orderFromString.to_string()).toBe(expected_order_str);
            // WAIVE results in a specific dict structure
            const generatedDict = orderFromString.to_dict();
            expect(generatedDict.type).toBe('Wait');
            expect(generatedDict.terrID).toBeUndefined(); // Or null depending on implementation
            expect(generatedDict.unitType).toBeUndefined();


            const orderFromDict = new WebDiplomacyOrder({type: 'Wait'} as WebDiplomacyOrderDict, defaultMapId, 'A');
            expect(orderFromDict.to_string()).toBe(expected_order_str);
        });
    });

});
