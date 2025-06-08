// diplomacy/daide/notifications.ts

import {
    StringTs, PowerTs, ProvinceTs, TurnTs, UnitTs,
    add_parentheses_ts, strip_parentheses_ts, parse_string_ts
} from './clauses';
import * as daideTokens from './tokens'; // Import all for token instances
import { Token } from './tokens';
import { daideBytesToString, daideStringToBytes } from './utils'; // Assuming utils.ts is available
import { DiplomacyMap as MapPlaceholder } from './possible_order_context'; // Using placeholder from another file for now

// Logger
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// Placeholder for engine Power object if needed by MissingOrdersNotification
interface EnginePower {
    name: string;
    units: string[]; // e.g., ["A PAR", "F BRE"]
    orders: Record<string, string>; // e.g., { "A PAR": "- BUR" }
    retreats: Record<string, string[]>; // e.g., { "A MUN": ["RUH", "SIL"] }
    homes: string[];
    centers: string[];
    // For OrderSplitter, if it's a class that processes order strings
    // adjust: any[]; // If 'adjust' property is used by MissingOrders' _build_adjustment_phase
}
// Placeholder for OrderSplitter - this is complex and would need its own file
interface OrderSplit {
    order_type: string;
    // other properties based on diplomacy.utils.splitter.OrderSplit
}
const OrderSplitterPlaceholder = (orderString: string): OrderSplit => {
    logger.warn(`OrderSplitterPlaceholder used for "${orderString}"`);
    // Dummy implementation
    if (orderString.includes(" B ")) return { order_type: 'B', unit: '', length: 0 };
    if (orderString.includes(" D ")) return { order_type: 'D', unit: '', length: 0 };
    return { order_type: 'UNKNOWN', unit: '', length: 0 };
};


export abstract class DaideNotification {
  protected _bytes: Uint8Array = new Uint8Array(0);
  protected _str: string = ''; // For caching string representation

  constructor() {}

  public toBytes(): Uint8Array {
    return this._bytes;
  }

  public toString(): string {
    if (!this._str && this._bytes.length > 0) {
      this._str = daideBytesToString(this._bytes);
    }
    return this._str;
  }

  protected concatBytes(byteArrays: Uint8Array[]): Uint8Array {
    let totalLength = 0;
    for (const arr of byteArrays) {
        totalLength += arr.length;
    }
    const result = new Uint8Array(totalLength);
    let offset = 0;
    for (const arr of byteArrays) {
        result.set(arr, offset);
        offset += arr.length;
    }
    return result;
  }
}

export class MapNameNotificationTs extends DaideNotification {
  constructor(map_name: string) {
    super();
    const mapNameClause = parse_string_ts(StringTs, map_name, 'raise');
    if (!mapNameClause) throw new Error("Failed to parse map name for MapNameNotification");

    this._bytes = this.concatBytes([
        daideTokens.MAP.toBytes(), // MAP token
        mapNameClause.toBytes()    // This is already ( 'n' 'a' 'm' 'e' )
    ]);
  }
}

export class HelloNotificationTs extends DaideNotification {
  constructor(power_name: string, passcode: number, level: number, deadline: number, rules: string[]) {
    super();
    const powerClause = parse_string_ts(PowerTs, power_name, 'raise');
    const passcodeToken = new Token({ from_int: passcode });
    if (!powerClause) throw new Error("Failed to parse power name for HelloNotification");

    const variantTokens: Uint8Array[] = [];
    if (rules.includes('NO_PRESS')) { // Example rule processing
      level = 0;
    }
    variantTokens.push(add_parentheses_ts(this.concatBytes([daideTokens.LVL.toBytes(), new Token({ from_int: level }).toBytes()])));

    if (deadline > 0) {
      const deadlineTokenBytes = new Token({ from_int: deadline }).toBytes();
      variantTokens.push(add_parentheses_ts(this.concatBytes([daideTokens.MTL.toBytes(), deadlineTokenBytes])));
      variantTokens.push(add_parentheses_ts(this.concatBytes([daideTokens.RTL.toBytes(), deadlineTokenBytes])));
      variantTokens.push(add_parentheses_ts(this.concatBytes([daideTokens.BTL.toBytes(), deadlineTokenBytes])));
    }
    if (rules.includes('NO_CHECK')) { // Example
      variantTokens.push(add_parentheses_ts(daideTokens.AOA.toBytes()));
    }
    if (rules.includes('PARTIAL_DRAWS_ALLOWED')) {
        variantTokens.push(add_parentheses_ts(daideTokens.PDA.toBytes()));
    }
    if (rules.includes('NO_PRESS_RETREATS')) { // Made up rule name
        variantTokens.push(add_parentheses_ts(daideTokens.NPR.toBytes()));
    }
     if (rules.includes('NO_PRESS_BUILDS')) { // Made up rule name
        variantTokens.push(add_parentheses_ts(daideTokens.NPB.toBytes()));
    }
    // PTL (Press Time Limit) would also be added here if applicable

    const allVariantsBytes = add_parentheses_ts(this.concatBytes(variantTokens));

    this._bytes = this.concatBytes([
      daideTokens.HLO.toBytes(),
      add_parentheses_ts(powerClause.toBytes()),
      add_parentheses_ts(passcodeToken.toBytes()),
      allVariantsBytes // This structure matches Python: HLO (power_bytes) (passcode_bytes) ((variant1_bytes)(variant2_bytes)...)
    ]);
  }
}

export class SupplyCenterNotificationTs extends DaideNotification {
  constructor(powers_centers: Record<string, string[]>, map_name: string, gameMapInstance?: MapPlaceholder) {
    super();
    const gameMap = gameMapInstance || new MapPlaceholder(map_name); // Use instance or load
    const remaining_scs = [...(gameMap.scs || [])]; // Ensure it's a new array
    const all_powers_bytes_grouped: Uint8Array[] = [];

    const sorted_power_names = Object.keys(powers_centers).sort();

    for (const power_name of sorted_power_names) {
      const centers = [...powers_centers[power_name]].sort();
      const powerClause = parse_string_ts(PowerTs, power_name, 'raise');
      if (!powerClause) throw new Error(`Invalid power name ${power_name} for SCO`);

      let current_power_byte_list: Uint8Array[] = [powerClause.toBytes()];
      for (const center of centers) {
        const scClause = parse_string_ts(ProvinceTs, center, 'raise');
        if (!scClause) throw new Error(`Invalid center ${center} for SCO`);
        current_power_byte_list.push(scClause.toBytes());
        const sc_idx = remaining_scs.indexOf(center); // Assuming center is short name
        if (sc_idx > -1) remaining_scs.splice(sc_idx, 1);
      }
      all_powers_bytes_grouped.push(add_parentheses_ts(this.concatBytes(current_power_byte_list)));
    }

    let unowned_sc_byte_list: Uint8Array[] = [daideTokens.UNO.toBytes()];
    remaining_scs.sort();
    for (const center of remaining_scs) {
      const scClause = parse_string_ts(ProvinceTs, center, 'raise');
      if (!scClause) throw new Error(`Invalid unowned center ${center} for SCO`);
      unowned_sc_byte_list.push(scClause.toBytes());
    }
    all_powers_bytes_grouped.push(add_parentheses_ts(this.concatBytes(unowned_sc_byte_list)));

    this._bytes = this.concatBytes([
        daideTokens.SCO.toBytes(),
        ...all_powers_bytes_grouped
    ]);
  }
}

// ... Stubs for CurrentPositionNotification, MissingOrdersNotification, etc.
export class CurrentPositionNotificationTs extends DaideNotification { constructor(phase_name: string, powers_units: Record<string, string[]>, powers_retreats: Record<string, Record<string, string[]>>) { super(); logger.warn("CurrentPositionNotificationTs not fully implemented"); } }
export class MissingOrdersNotificationTs extends DaideNotification { constructor(phase_name: string, power: EnginePower) { super(); logger.warn("MissingOrdersNotificationTs not fully implemented"); this._bytes = daideTokens.MIS.toBytes(); /* Simplified */ } }
export class OrderResultNotificationTs extends DaideNotification { constructor(phase_name: string, order_bytes: Uint8Array, results: number[]) { super(); logger.warn("OrderResultNotificationTs not fully implemented"); } }
export class TimeToDeadlineNotificationTs extends DaideNotification { constructor(seconds: number) { super(); this._bytes = this.concatBytes([daideTokens.TME.toBytes(), add_parentheses_ts(new Token({from_int: seconds}).toBytes())]); } }
export class PowerInCivilDisorderNotificationTs extends DaideNotification { constructor(power_name: string) { super(); const p = parse_string_ts(PowerTs, power_name, 'raise'); if(!p) throw new Error("Invalid power"); this._bytes = this.concatBytes([daideTokens.CCD.toBytes(), add_parentheses_ts(p.toBytes())]);} }
export class PowerIsEliminatedNotificationTs extends DaideNotification { constructor(power_name: string) { super(); const p = parse_string_ts(PowerTs, power_name, 'raise'); if(!p) throw new Error("Invalid power"); this._bytes = this.concatBytes([daideTokens.OUT.toBytes(), add_parentheses_ts(p.toBytes())]);} }
export class DrawNotificationTs extends DaideNotification { constructor() { super(); this._bytes = daideTokens.DRW.toBytes(); } }
export class MessageFromNotificationTs extends DaideNotification { constructor(from_power_name: string, to_power_names: string[], message_content_daide_str: string) { super(); logger.warn("MessageFromNotificationTs not fully implemented. String to bytes conversion needed."); const fromP = parse_string_ts(PowerTs,from_power_name,'raise')?.toBytes() || new Uint8Array(0); const toPs = this.concatBytes(to_power_names.map(pn => parse_string_ts(PowerTs,pn,'raise')?.toBytes() || new Uint8Array(0))); const msgBytes = daideStringToBytes(message_content_daide_str); this._bytes = this.concatBytes([daideTokens.FRM.toBytes(), add_parentheses_ts(fromP), add_parentheses_ts(toPs), add_parentheses_ts(msgBytes) ]); } }
export class SoloNotificationTs extends DaideNotification { constructor(power_name: string) { super(); const p = parse_string_ts(PowerTs, power_name, 'raise'); if(!p) throw new Error("Invalid power"); this._bytes = this.concatBytes([daideTokens.SLO.toBytes(), add_parentheses_ts(p.toBytes())]);} }
export class SummaryNotificationTs extends DaideNotification { constructor(phase_name: string, powers: EnginePower[], daide_users: any[], years_of_elimination: (number|null)[]) { super(); logger.warn("SummaryNotificationTs not fully implemented"); } }
export class TurnOffNotificationTs extends DaideNotification { constructor() { super(); this._bytes = daideTokens.OFF.toBytes(); } }


// Aliases
export const MAP_NOTIFICATION = MapNameNotificationTs;
export const HLO_NOTIFICATION = HelloNotificationTs;
export const SCO_NOTIFICATION = SupplyCenterNotificationTs;
export const NOW_NOTIFICATION = CurrentPositionNotificationTs;
export const MIS_NOTIFICATION = MissingOrdersNotificationTs;
export const ORD_NOTIFICATION = OrderResultNotificationTs;
export const TME_NOTIFICATION = TimeToDeadlineNotificationTs;
export const CCD_NOTIFICATION = PowerInCivilDisorderNotificationTs;
export const OUT_NOTIFICATION = PowerIsEliminatedNotificationTs;
export const DRW_NOTIFICATION = DrawNotificationTs;
export const FRM_NOTIFICATION = MessageFromNotificationTs;
export const SLO_NOTIFICATION = SoloNotificationTs;
export const SMR_NOTIFICATION = SummaryNotificationTs;
export const OFF_NOTIFICATION = TurnOffNotificationTs;
