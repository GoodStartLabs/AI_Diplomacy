// diplomacy/integration/webdiplomacy_net/utils.ts

/**
 * Represents a game ID and country ID pair.
 */
export interface GameIdCountryId {
    game_id: number | string; // game_id can sometimes be string in webdiplomacy context
    country_id: number;
}

interface MapData {
    powers: string[];
    locs: (string | null)[];
    ix_to_power?: Record<number, string>;
    power_to_ix?: Record<string, number>;
    ix_to_loc?: Record<number, string>;
    loc_to_ix?: Record<string, number>;
}

interface WebDiplomacyCache {
    ix_to_map: Record<number, string>;
    map_to_ix: Record<string, number>;
    [key: string]: any; // For map names like 'standard'
    [key: number]: MapData | undefined; // For map IDs like 1, 15, 23
}

export const CACHE: WebDiplomacyCache = {
    ix_to_map: { 1: 'standard', 15: 'standard_france_austria', 23: 'standard_germany_italy' },
    map_to_ix: { 'standard': 1, 'standard_france_austria': 15, 'standard_germany_italy': 23 },
};

const standardMapData: MapData = {
    powers: ['GLOBAL', 'ENGLAND', 'FRANCE', 'ITALY', 'GERMANY', 'AUSTRIA', 'TURKEY', 'RUSSIA'],
    locs: [null, 'CLY', 'EDI', 'LVP', 'YOR', 'WAL', 'LON', 'POR', 'SPA', 'NAF', 'TUN', 'NAP', 'ROM', 'TUS',
             'PIE', 'VEN', 'APU', 'GRE', 'ALB', 'SER', 'BUL', 'RUM', 'CON', 'SMY', 'ANK', 'ARM', 'SYR', 'SEV',
             'UKR', 'WAR', 'LVN', 'MOS', 'STP', 'FIN', 'SWE', 'NWY', 'DEN', 'KIE', 'BER', 'PRU', 'SIL', 'MUN',
             'RUH', 'HOL', 'BEL', 'PIC', 'BRE', 'PAR', 'BUR', 'MAR', 'GAS', 'BAR', 'NWG', 'NTH', 'SKA', 'HEL',
             'BAL', 'BOT', 'NAO', 'IRI', 'ENG', 'MAO', 'WES', 'LYO', 'TYS', 'ION', 'ADR', 'AEG', 'EAS', 'BLA',
             'TYR', 'BOH', 'VIE', 'TRI', 'BUD', 'GAL', 'SPA/NC', 'SPA/SC', 'STP/NC', 'STP/SC', 'BUL/EC',
             'BUL/SC']
};

const franceAustriaMapData: MapData = {
    powers: ['GLOBAL', 'FRANCE', 'AUSTRIA'],
    locs: [null, 'CLY', 'EDI', 'LVP', 'YOR', 'WAL', 'LON', 'POR', 'SPA', 'SPA/NC', 'SPA/SC', 'NAF', 'TUN',
             'NAP', 'ROM', 'TUS', 'PIE', 'VEN', 'APU', 'GRE', 'ALB', 'SER', 'BUL', 'BUL/EC', 'BUL/SC', 'RUM',
             'CON', 'SMY', 'ANK', 'ARM', 'SYR', 'SEV', 'UKR', 'WAR', 'LVN', 'MOS', 'STP', 'STP/NC', 'STP/SC',
             'FIN', 'SWE', 'NWY', 'DEN', 'KIE', 'BER', 'PRU', 'SIL', 'MUN', 'RUH', 'HOL', 'BEL', 'PIC', 'BRE',
             'PAR', 'BUR', 'MAR', 'GAS', 'BAR', 'NWG', 'NTH', 'SKA', 'HEL', 'BAL', 'BOT', 'NAO', 'IRI', 'ENG',
             'MAO', 'WES', 'LYO', 'TYS', 'ION', 'ADR', 'AEG', 'EAS', 'BLA', 'TYR', 'BOH', 'VIE', 'TRI', 'BUD',
             'GAL']
};

const germanyItalyMapData: MapData = {
    powers: ['GLOBAL', 'GERMANY', 'ITALY'],
    locs: [null, 'CLY', 'EDI', 'LVP', 'YOR', 'WAL', 'LON', 'POR', 'SPA', 'SPA/NC', 'SPA/SC', 'NAF', 'TUN',
             'NAP', 'ROM', 'TUS', 'PIE', 'VEN', 'APU', 'GRE', 'ALB', 'SER', 'BUL', 'BUL/EC', 'BUL/SC', 'RUM',
             'CON', 'SMY', 'ANK', 'ARM', 'SYR', 'SEV', 'UKR', 'WAR', 'LVN', 'MOS', 'STP', 'STP/NC', 'STP/SC',
             'FIN', 'SWE', 'NWY', 'DEN', 'KIE', 'BER', 'PRU', 'SIL', 'MUN', 'RUH', 'HOL', 'BEL', 'PIC', 'BRE',
             'PAR', 'BUR', 'MAR', 'GAS', 'BAR', 'NWG', 'NTH', 'SKA', 'HEL', 'BAL', 'BOT', 'NAO', 'IRI', 'ENG',
             'MAO', 'WES', 'LYO', 'TYS', 'ION', 'ADR', 'AEG', 'EAS', 'BLA', 'TYR', 'BOH', 'VIE', 'TRI', 'BUD',
             'GAL']
};

CACHE[1] = standardMapData;
CACHE['standard'] = standardMapData;
CACHE[15] = franceAustriaMapData;
CACHE['standard_france_austria'] = franceAustriaMapData;
CACHE[23] = germanyItalyMapData;
CACHE['standard_germany_italy'] = germanyItalyMapData;


function populateMapSpecificCache(mapData: MapData): void {
    mapData.ix_to_power = {};
    mapData.power_to_ix = {};
    mapData.ix_to_loc = {};
    mapData.loc_to_ix = {};

    mapData.powers.forEach((powerName, index) => {
        mapData.ix_to_power![index] = powerName;
        mapData.power_to_ix![powerName] = index;
    });

    mapData.locs.forEach((locName, index) => {
        if (index === 0 || locName === null) { // Skip the null at index 0
            return;
        }
        mapData.ix_to_loc![index] = locName;
        mapData.loc_to_ix![locName] = index;
    });
}

// Populate the cache for each map type
populateMapSpecificCache(CACHE[1]!);
populateMapSpecificCache(CACHE[15]!);
populateMapSpecificCache(CACHE[23]!);

/**
 * Helper function to get map-specific data from the cache.
 * @param mapIdOrName - The ID (1, 15, 23) or name ('standard', etc.) of the map.
 * @returns The map-specific data, or undefined if not found.
 */
export function getMapData(mapIdOrName: number | string): MapData | undefined {
    if (typeof mapIdOrName === 'number') {
        return CACHE[mapIdOrName];
    } else if (typeof mapIdOrName === 'string' && CACHE[mapIdOrName]) {
        return CACHE[mapIdOrName] as MapData;
    }
    return undefined;
}

// Example usage (optional, can be removed)
// const standardData = getMapData('standard');
// if (standardData && standardData.power_to_ix) {
//   console.log("Index of ENGLAND in standard map:", standardData.power_to_ix['ENGLAND']);
// }
// const map15Data = getMapData(15);
// if (map15Data && map15Data.ix_to_loc) {
//   console.log("Location at index 5 in map 15:", map15Data.ix_to_loc[5]);
// }
