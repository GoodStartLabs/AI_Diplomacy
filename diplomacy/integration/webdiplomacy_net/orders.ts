// diplomacy/integration/webdiplomacy_net/orders.ts

import { DiplomacyGame } from '../../../engine/game';
import { DiplomacyMap } from '../../../engine/map';
import { CACHE, getMapData } from './utils';
import { WebDiplomacyOrderDict } from './game'; // Assuming this is defined for the dict structure

// --- Helper Functions (adapted from Python) ---

/**
 * Checks if two locations are adjacent (for convoy purposes).
 */
function is_adjacent_for_convoy(loc1: string, loc2: string, map: DiplomacyMap): boolean {
    const area1 = map.get_province_type(loc1.substring(0,3));
    const area2 = map.get_province_type(loc2.substring(0,3));

    if (area1 === 'LAND' || area2 === 'LAND') return false;
    if (area1 === 'WATER' && area2 === 'WATER') return map.abuts('F', loc1, '-', loc2);

    let coastLoc = '';
    let waterLoc = '';
    if (area1 === 'COAST' && area2 === 'WATER') {
        coastLoc = loc1;
        waterLoc = loc2;
    } else if (area2 === 'COAST' && area1 === 'WATER') {
        coastLoc = loc2;
        waterLoc = loc1;
    } else {
        return false; // Both COAST or other combos not allowed for direct convoy adjacency step
    }

    const coastsOfCoastLoc = map.find_coasts(coastLoc); // find_coasts expects canonical name
    return coastsOfCoastLoc.some(locWithCoast => map.abuts('F', locWithCoast, '-', waterLoc));
}

/**
 * Finds a convoy path from src to dest.
 * Note: This is a simplified version. Python's version uses pre-calculated map.convoy_paths.
 * This version will attempt a basic BFS if map.convoy_paths is not available or suitable.
 */
export function find_convoy_path(
    src: string, // Base loc, e.g., PAR
    dest: string, // Base loc, e.g., LON
    map: DiplomacyMap,
    game?: DiplomacyGame, // Used to get actual fleet locations
    including?: string | string[],
    excluding?: string | string[]
): string[] { // Returns [src, fleet1, ..., fleetN, dest]
    if (map.get_province_type(src) !== 'COAST' || map.get_province_type(dest) !== 'COAST') {
        return [];
    }

    const includeProvinces = Array.isArray(including) ? including : (including ? [including] : []);
    const excludeProvinces = Array.isArray(excluding) ? excluding : (excluding ? [excluding] : []);

    const waterProvinces = new Set(map.get_all_sea_provinces());
    let availableFleets = new Set(waterProvinces); // Initially, all water provinces are potential fleet spots

    if (game) {
        availableFleets = new Set();
        for (const powerState of Object.values(game.powers)) {
            for (const unit of powerState.units) {
                if (unit.type === 'FLEET' && waterProvinces.has(unit.location)) {
                    availableFleets.add(unit.location);
                }
            }
        }
    }

    // Simple BFS for convoy path - this is a placeholder for the more complex Python logic
    // that uses pre-calculated map.convoy_paths.
    // This BFS will find *a* path, not necessarily the one webdiplomacy expects or the most optimal.
    // For webdiplomacy.net, the exact path matters for the API.
    // TODO: Replicate Python's map.convoy_paths usage if this BFS is insufficient.

    const queue: { path: string[], remainingFleets: Set<string> }[] = [{ path: [src], remainingFleets: new Set(availableFleets) }];
    const visitedPaths = new Set<string>(); // To avoid cycles with same path prefix

    while (queue.length > 0) {
        const { path, remainingFleets } = queue.shift()!;
        const currentLoc = path[path.length - 1];

        if (path.length > 1 && is_adjacent_for_convoy(currentLoc, dest, map)) { // Path.length > 1 means at least one fleet
            const finalPath = [...path, dest];
            // Check 'including' and 'excluding' constraints
            const pathFleets = finalPath.slice(1, -1);
            if (includeProvinces.every(inc => pathFleets.includes(inc)) &&
                !excludeProvinces.some(exc => pathFleets.includes(exc))) {
                return finalPath;
            }
        }

        if (path.length > map.locs.length / 2) continue; // Safety break for very long paths

        for (const fleetLoc of remainingFleets) {
            if (is_adjacent_for_convoy(currentLoc, fleetLoc, map)) {
                const newPath = [...path, fleetLoc];
                const newPathKey = newPath.join(',');
                if (!visitedPaths.has(newPathKey)) {
                    visitedPaths.add(newPathKey);
                    const newRemainingFleets = new Set(remainingFleets);
                    newRemainingFleets.delete(fleetLoc);
                    queue.push({ path: newPath, remainingFleets: newRemainingFleets });
                }
            }
        }
    }
    return []; // No path found
}


export class WebDiplomacyOrder {
    public order_str: string = '';
    public order_dict: Partial<WebDiplomacyOrderDict> = {}; // Use partial as it's built progressively
    private map_name: string;
    private map_id: number;
    private phase_type: 'M' | 'R' | 'A'; // Movement, Retreat, Adjustment

    constructor(
        order: string | WebDiplomacyOrderDict,
        mapNameOrId: string | number,
        phaseType?: 'M' | 'R' | 'A',
        private game?: DiplomacyGame // Optional game object for context (e.g., convoy paths)
    ) {
        const mapData = getMapData(mapNameOrId);
        if (!mapData) {
            throw new Error(`Unsupported map: ${mapNameOrId}`);
        }
        this.map_name = typeof mapNameOrId === 'string' ? mapNameOrId : CACHE.ix_to_map[mapNameOrId];
        this.map_id = typeof mapNameOrId === 'number' ? mapNameOrId : CACHE.map_to_ix[mapNameOrId];

        this.phase_type = phaseType || 'M'; // Default to movement phase

        if (typeof order === 'string') {
            this._build_from_string(order);
        } else if (typeof order === 'object') {
            this._build_from_dict(order);
        } else {
            throw new Error('Order must be a string or a dictionary.');
        }
    }

    private _get_map_data(): MapData | undefined {
        return getMapData(this.map_id);
    }

    private _build_from_string(order: string): void {
        let processedOrder = order;
        if (this.phase_type === 'R') {
            processedOrder = processedOrder.replace(/\s-\s/g, ' R '); // Convert move to retreat
        }
        const words = processedOrder.split(/\s+/);

        if (words.length === 1 && words[0].toUpperCase() === 'WAIVE') {
            this.order_str = 'WAIVE';
            this.order_dict = { type: 'Wait', terrID: undefined, unitType: undefined, toTerrID: undefined, fromTerrID: undefined, viaConvoy: undefined };
            return;
        }
        if (words.length < 3) { console.error(`Order too short: ${order}`); return; }

        const unitTypeChar = words[0].toUpperCase();
        const locName = words[1].toUpperCase();
        const orderTypeChar = words[2].toUpperCase();

        if (unitTypeChar !== 'A' && unitTypeChar !== 'F') { console.error(`Invalid unit type: ${unitTypeChar}`); return; }
        const mapData = this._get_map_data();
        if (!mapData || !mapData.loc_to_ix || !mapData.loc_to_ix[locName]) { console.error(`Invalid location: ${locName} for map ${this.map_name}`); return; }

        const unitType = unitTypeChar === 'A' ? 'Army' : 'Fleet';
        const terrID = mapData.loc_to_ix![locName]; // mapData and loc_to_ix confirmed by earlier check

        this.order_str = processedOrder; // Store the potentially modified order string (e.g., for retreats)
        this.order_dict.terrID = terrID;
        this.order_dict.unitType = unitType;

        if (orderTypeChar === 'H') {
            this.order_dict.type = 'Hold';
        } else if (orderTypeChar === '-') { // Move or Retreat (if phase R)
            if (words.length < 4) { console.error(`[Move/Retreat] Order too short: ${order}`); return; }
            const toLocName = words[3].toUpperCase();
            if (!mapData.loc_to_ix![toLocName]) { console.error(`[Move/Retreat] Invalid target location: ${toLocName}`); return; }
            this.order_dict.toTerrID = mapData.loc_to_ix![toLocName];

            if (this.phase_type === 'R') { // Already pre-processed ' - ' to ' R '
                this.order_dict.type = 'Retreat';
            } else {
                this.order_dict.type = 'Move';
                const viaConvoy = words[words.length - 1].toUpperCase() === 'VIA';
                this.order_dict.viaConvoy = viaConvoy ? 'Yes' : 'No';
                if (viaConvoy && unitType === 'Army' && this.game) {
                    const path = find_convoy_path(locName, toLocName, this.game.map, this.game);
                    if (path.length > 2) { // src, fleet1..., dest
                        (this.order_dict as any).convoyPath = path.slice(1, -1).map(loc => mapData.loc_to_ix![loc]);
                    }
                }
            }
        } else if (orderTypeChar === 'S') { // Support
            if (words.length < 5) { console.error(`[Support] Order too short: ${order}`); return; }
            const supportedUnitLocName = words[3].toUpperCase();
            if (!mapData.loc_to_ix![supportedUnitLocName]) { console.error(`[Support] Invalid supported unit location: ${supportedUnitLocName}`); return; }

            if (words.length > 5 && words[4].toUpperCase() === '-') { // Support Move
                if (words.length < 6) { console.error(`[Support Move] Order too short: ${order}`); return; }
                const supportedMoveToLocName = words[5].toUpperCase();
                if (!mapData.loc_to_ix![supportedMoveToLocName]) { console.error(`[Support Move] Invalid target location: ${supportedMoveToLocName}`); return; }

                this.order_dict.type = 'Support move';
                this.order_dict.fromTerrID = mapData.loc_to_ix![supportedUnitLocName]; // Unit being supported is 'from'
                this.order_dict.toTerrID = mapData.loc_to_ix![supportedMoveToLocName]; // Destination of supported unit
            } else { // Support Hold
                this.order_dict.type = 'Support hold';
                this.order_dict.toTerrID = mapData.loc_to_ix![supportedUnitLocName]; // Location of unit being held
            }
        } else if (orderTypeChar === 'C') { // Convoy
            if (words.length < 6 || words[3].toUpperCase() !== 'A' || words[5].toUpperCase() !== '-') { // e.g. F ENG C A BRE - PIC
                console.error(`[Convoy] Malformed convoy order: ${order}. Expecting F X C A Y - Z`); return;
            }
            const convoyedUnitFromLocName = words[4].toUpperCase();
            const convoyedUnitToLocName = words[6].toUpperCase();
            if (!mapData.loc_to_ix![convoyedUnitFromLocName]) { console.error(`[Convoy] Invalid convoy source: ${convoyedUnitFromLocName}`); return; }
            if (!mapData.loc_to_ix![convoyedUnitToLocName]) { console.error(`[Convoy] Invalid convoy target: ${convoyedUnitToLocName}`); return; }

            this.order_dict.type = 'Convoy';
            this.order_dict.fromTerrID = mapData.loc_to_ix![convoyedUnitFromLocName];
            this.order_dict.toTerrID = mapData.loc_to_ix![convoyedUnitToLocName];
            if (this.game) {
                 const path = find_convoy_path(convoyedUnitFromLocName, convoyedUnitToLocName, this.game.map, this.game, locName);
                 if (path.length > 2) {
                    (this.order_dict as any).convoyPath = path.slice(1, -1).map(l => mapData.loc_to_ix![l]);
                 }
            }
        } else if (orderTypeChar === 'D') { // Disband
            this.order_dict.type = this.phase_type === 'A' ? 'Destroy' : 'Disband';
            if (this.phase_type === 'A') { // For adjustment phase, toTerrID is the location of unit being destroyed
                 this.order_dict.toTerrID = terrID;
            }
        } else if (orderTypeChar === 'B') { // Build
            this.order_dict.type = unitType === 'Army' ? 'Build Army' : 'Build Fleet';
            this.order_dict.toTerrID = terrID; // Location of build is toTerrID for API
        } else {
            console.error(`Unknown order type char: ${orderTypeChar} in ${order}`);
        }
    }

    private _build_from_dict(orderDict: WebDiplomacyOrderDict): void {
        this.order_dict = { ...orderDict };
        const mapData = this._get_map_data();
        if (!mapData || !mapData.ix_to_loc) { console.error("Map data not available for dict parsing"); return; }

        const { type, terrID, unitType, toTerrID, fromTerrID, viaConvoy } = orderDict;

        // Determine the primary location for the unit, using toTerrID for builds/destroys if terrID is null
        const primaryTerrID = (type === 'Build Army' || type === 'Build Fleet' || type === 'Destroy') ? toTerrID : terrID;
        const locName = primaryTerrID ? mapData.ix_to_loc[primaryTerrID] : null;
        const toLocName = toTerrID ? mapData.ix_to_loc[toTerrID] : null;
        const fromLocName = fromTerrID ? mapData.ix_to_loc[fromTerrID] : null;

        let unitChar = '?'; // Default for WAIVE or unknown
        if (type === 'Build Army') unitChar = 'A';
        else if (type === 'Build Fleet') unitChar = 'F';
        else if (unitType) unitChar = unitType[0];


        if (!locName && type !== 'Wait') { console.error("Location name missing for order", orderDict); this.order_str = "ERROR_MISSING_LOC"; return; }

        switch (type) {
            case 'Hold': this.order_str = `${unitChar} ${locName} H`; break;
            case 'Move': this.order_str = `${unitChar} ${locName} - ${toLocName}${viaConvoy === 'Yes' ? ' VIA' : ''}`; break;
            case 'Support hold': this.order_str = `${unitChar} ${locName} S ${toLocName}`; break;
            case 'Support move': this.order_str = `${unitChar} ${locName} S ${fromLocName} - ${toLocName}`; break;
            case 'Convoy': this.order_str = `${unitChar} ${locName} C A ${fromLocName} - ${toLocName}`; break;
            case 'Retreat': this.order_str = `${unitChar} ${locName} R ${toLocName}`; break;
            case 'Disband': this.order_str = `${unitChar} ${locName} D`; break;
            case 'Build Army': this.order_str = `A ${locName} B`; break;
            case 'Build Fleet': this.order_str = `F ${locName} B`; break;
            case 'Wait': this.order_str = 'WAIVE'; break;
            case 'Destroy': this.order_str = `${unitChar} ${locName} D`; break;
            default: console.error(`Unknown order type in dict: ${type}`); this.order_str = 'ERROR_UNKNOWN_ORDER_TYPE';
        }
    }

    isValid(): boolean {
        return !!this.order_str && !this.order_str.startsWith('ERROR');
    }

    to_string(): string {
        return this.order_str;
    }

    to_norm_string(): string {
        let normStr = this.order_str;
        if (normStr.endsWith(' D') && this.order_dict.unitType === '?') { // Special case for implicit disband from Python
            normStr = `? ${this.order_str.substring(2)}`;
        }
        return normStr
            .replace(/\sS\sA\s/g, ' S ')
            .replace(/\sS\sF\s/g, ' S ')
            .replace(/\sC\sA\s/g, ' C ')
            .replace(/\sC\sF\s/g, ' C ')
            .replace(/\sVIA$/, '');
    }

    to_dict(): Partial<WebDiplomacyOrderDict> {
        // Ensure essential fields are present, even if undefined from partial
        return {
            terrID: this.order_dict.terrID,
            unitType: this.order_dict.unitType as ('Army' | 'Fleet' | undefined),
            type: this.order_dict.type!, // type should always be defined
            toTerrID: this.order_dict.toTerrID,
            fromTerrID: this.order_dict.fromTerrID,
            viaConvoy: this.order_dict.viaConvoy as ('Yes' | 'No' | undefined),
            convoyPath: (this.order_dict as any).convoyPath, // Keep if already set
        };
    }
}
