// diplomacy/daide/requests.ts

import {
    AbstractClauseTs, StringTs, NumberTs, PowerTs, OrderTs, TurnTs, SingleTokenTs,
    strip_parentheses_ts, break_next_group_ts, parse_bytes_ts
} from './clauses';
import * as daideTokens from './tokens'; // Import all tokens
import { Token } from './tokens';

// Logger
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// Base DaideRequest class
// This replaces the Python DaideRequest which inherited from _AbstractGameRequest.
// For DAIDE server-side parsing, we might not need all fields from _AbstractGameRequest
// immediately, or they are added by the ConnectionHandler/MasterServer context.
export abstract class DaideRequest {
  protected _bytes: Uint8Array = new Uint8Array(0);
  protected _str: string = ''; // Full string representation of the DAIDE command

  // Context fields that might be populated by ConnectionHandler or further up
  public game_id?: string;
  public token?: string; // Client's channel token
  public game_role?: string; // Role in the game (e.g. power name, OBS)
  public phase?: string; // Current game phase

  constructor() {}

  // This method is called by RequestBuilderTs.fromBytes AFTER the specific request object is instantiated.
  // It receives the full original DAIDE byte sequence for the command.
  public abstract parseBytes(daideBytes: Uint8Array): void;

  public toBytes(): Uint8Array {
    return this._bytes;
  }

  public toString(): string {
    return this._str;
  }

  // Helper to build the basic string representation from any DAIDE byte sequence
  protected buildBaseStringRepresentation(daideBytes: Uint8Array): void {
    let tempStr = '';
    for (let i = 0; i < daideBytes.length; i += 2) {
      const tokenBytes = daideBytes.slice(i, i + 2);
      if (tokenBytes.length < 2) break; // Should not happen if length is even
      const token = new Token({ from_bytes: tokenBytes });
      const new_str = token.toString();
      const pad = (tempStr === '' || tempStr.endsWith('(') || new_str === ')' || (daideTokens.isAsciiToken(token) && new_str !== '(')) ? '' : ' ';
      tempStr = tempStr + pad + new_str;
    }
    this._str = tempStr;
  }
}

// Specific DAIDE Request Classes

export class NameRequestTs extends DaideRequest {
  __type__ = "NameRequest"; // For potential type guarding or mapping
  client_name: string = '';
  client_version: string = '';

  constructor() { super(); }

  parseBytes(daideBytes: Uint8Array): void {
    this._bytes = daideBytes; // Store raw bytes
    this.buildBaseStringRepresentation(daideBytes); // Build basic string like "NME (client_name_str) (client_version_str)"

    let remainingBytes = daideBytes;
    const [lead_token_obj, r0] = parse_bytes_ts(SingleTokenTs, remainingBytes);
    if (!lead_token_obj || lead_token_obj.getToken()?.toString() !== 'NME') throw new Error('Expected NME request');
    remainingBytes = r0;

    const [client_name_obj, r1] = parse_bytes_ts(StringTs, remainingBytes);
    if (!client_name_obj?.isValid) throw new Error('Invalid client name string in NME request');
    this.client_name = client_name_obj.toString();
    remainingBytes = r1;

    const [client_version_obj, r2] = parse_bytes_ts(StringTs, remainingBytes);
    if (!client_version_obj?.isValid) throw new Error('Invalid client version string in NME request');
    this.client_version = client_version_obj.toString();
    remainingBytes = r2;

    if (remainingBytes.length > 0) throw new Error(`NME request malformed, ${remainingBytes.length} bytes remaining.`);
  }
}

export class ObserverRequestTs extends DaideRequest {
  __type__ = "ObserverRequest";
  constructor() { super(); }
  parseBytes(daideBytes: Uint8Array): void {
    this._bytes = daideBytes; this.buildBaseStringRepresentation(daideBytes);
    const [lead_token_obj, r0] = parse_bytes_ts(SingleTokenTs, daideBytes);
    if (!lead_token_obj || lead_token_obj.getToken()?.toString() !== 'OBS') throw new Error('Expected OBS request');
    if (r0.length > 0) throw new Error(`OBS request malformed, ${r0.length} bytes remaining.`);
  }
}

export class IAmRequestTs extends DaideRequest {
  __type__ = "IAmRequest";
  power_name: string = ''; // Long name, e.g. "AUSTRIA"
  passcode: string = ''; // Parsed as string token in Python example

  constructor() { super(); }
  parseBytes(daideBytes: Uint8Array): void {
    this._bytes = daideBytes; this.buildBaseStringRepresentation(daideBytes);
    let remainingBytes = daideBytes;

    const [lead_token_obj, r0] = parse_bytes_ts(SingleTokenTs, remainingBytes);
    if (!lead_token_obj || lead_token_obj.getToken()?.toString() !== 'IAM') throw new Error('Expected IAM request');
    remainingBytes = r0;

    const [power_group_bytes, r1] = break_next_group_ts(remainingBytes);
    if (!power_group_bytes) throw new Error("IAM: Missing power group");
    let inner_power_group = strip_parentheses_ts(power_group_bytes);
    const [power_obj, r_pg] = parse_bytes_ts(PowerTs, inner_power_group);
    if (!power_obj?.isValid) throw new Error("IAM: Invalid power in power group");
    if (r_pg.length > 0) throw new Error("IAM: Extra bytes in power group");
    this.power_name = power_obj.toString(); // PowerTs.toString() gives long name
    remainingBytes = r1;

    const [passcode_group_bytes, r2] = break_next_group_ts(remainingBytes);
    if (!passcode_group_bytes) throw new Error("IAM: Missing passcode group");
    let inner_passcode_group = strip_parentheses_ts(passcode_group_bytes);
    // Python parses passcode as SingleToken, implying it could be non-numeric string.
    const [passcode_obj, r_pcg] = parse_bytes_ts(StringTs, add_parentheses_ts(inner_passcode_group)); // StringTs expects parentheses
    if (!passcode_obj?.isValid) throw new Error("IAM: Invalid passcode string");
    // Python code: passcode, passcode_group_bytes = parse_bytes(SingleToken, passcode_group_bytes)
    // This means passcode is a single token, not a StringTs. Let's adjust.
    // Re-parsing passcode as a sequence of single tokens if it's not a simple string.
    // For simplicity, if passcode is simple string/number, StringTs or NumberTs might be better.
    // Python's `str(passcode)` suggests it resolves to a string.
    // Let's assume passcode is a string of characters, each a token.
    this.passcode = "";
    let current_passcode_bytes = inner_passcode_group;
    while(current_passcode_bytes.length > 0) {
        const [char_token_obj, next_passcode_bytes] = parse_bytes_ts(SingleTokenTs, current_passcode_bytes);
        if (!char_token_obj?.isValid) throw new Error("IAM: Invalid token in passcode");
        this.passcode += char_token_obj.toString();
        current_passcode_bytes = next_passcode_bytes;
    }
    remainingBytes = r2;

    if (remainingBytes.length > 0) throw new Error(`IAM request malformed, ${remainingBytes.length} bytes remaining.`);
  }
}

// ... Other request classes will follow similar pattern ...
// HelloRequest, MapRequest, MapDefinitionRequest, SupplyCentreOwnershipRequest, CurrentPositionRequest, HistoryRequest
// SubmitOrdersRequest, MissingOrdersRequest, GoFlagRequest, TimeToDeadlineRequest, DrawRequest, SendMessageRequest
// NotRequest, AcceptRequest, RejectRequest, ParenthesisErrorRequest, SyntaxErrorRequest, AdminMessageRequest

// Stubs for remaining classes for now
export class HelloRequestTs extends DaideRequest { __type__ = "HelloRequest"; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class MapRequestTs extends DaideRequest { __type__ = "MapRequest"; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class MapDefinitionRequestTs extends DaideRequest { __type__ = "MapDefinitionRequest"; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class SupplyCentreOwnershipRequestTs extends DaideRequest { __type__ = "SupplyCentreOwnershipRequest"; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class CurrentPositionRequestTs extends DaideRequest { __type__ = "CurrentPositionRequest"; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }

export class HistoryRequestTs extends DaideRequest {
  __type__ = "HistoryRequest";
  phase: string = ''; // Parsed from Turn clause
  constructor() { super(); }
  parseBytes(daideBytes: Uint8Array): void {
    this._bytes = daideBytes; this.buildBaseStringRepresentation(daideBytes);
    let remainingBytes = daideBytes;
    const [lead_token_obj, r0] = parse_bytes_ts(SingleTokenTs, remainingBytes);
    if (!lead_token_obj || lead_token_obj.getToken()?.toString() !== 'HST') throw new Error('Expected HST request');
    remainingBytes = r0;
    const [turn_obj, r1] = parse_bytes_ts(TurnTs, remainingBytes);
    if (!turn_obj?.isValid) throw new Error("HST: Invalid Turn clause");
    this.phase = turn_obj.toString();
    remainingBytes = r1;
    if (remainingBytes.length > 0) throw new Error(`HST request malformed, ${remainingBytes.length} bytes remaining.`);
  }
}

export class SubmitOrdersRequestTs extends DaideRequest {
  __type__ = "SubmitOrdersRequest";
  power_name: string | null = null; // Long name
  parsedPhase: string = ''; // Parsed from optional Turn clause
  orders: string[] = []; // Array of string orders

  constructor() { super(); }
  parseBytes(daideBytes: Uint8Array): void {
    this._bytes = daideBytes; this.buildBaseStringRepresentation(daideBytes);
    let remainingBytes = daideBytes;
    const [lead_token_obj, r0] = parse_bytes_ts(SingleTokenTs, remainingBytes);
    if (!lead_token_obj || lead_token_obj.getToken()?.toString() !== 'SUB') throw new Error('Expected SUB request');
    remainingBytes = r0;

    const [turn_obj, r_turn] = parse_bytes_ts(TurnTs, remainingBytes, 'ignore'); // Optional Turn
    if (turn_obj?.isValid) {
        this.parsedPhase = turn_obj.toString();
        remainingBytes = r_turn;
    }

    const parsedOrders: OrderTs[] = [];
    while(remainingBytes.length > 0) {
        const [order_obj, r_order] = parse_bytes_ts(OrderTs, remainingBytes);
        if (!order_obj?.isValid) throw new Error("SUB: Invalid Order clause in submission");
        parsedOrders.push(order_obj);
        remainingBytes = r_order;
    }
    if (parsedOrders.length > 0) {
        this.power_name = parsedOrders[0].power_name; // Assuming all orders for same power
        this.orders = parsedOrders.map(o => o.toString());
    }
    // Note: Python sets self.phase, self.power_name, self.orders.
    // this.phase is part of DaideRequest base, might be game context phase.
    // parsedPhase stores phase from message if present.
  }
}

export class MissingOrdersRequestTs extends DaideRequest { __type__ = "MissingOrdersRequest"; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class GoFlagRequestTs extends DaideRequest { __type__ = "GoFlagRequest"; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }

export class TimeToDeadlineRequestTs extends DaideRequest {
  __type__ = "TimeToDeadlineRequest";
  seconds: number | null = null;
  constructor() { super(); }
  parseBytes(daideBytes: Uint8Array): void {
    this._bytes = daideBytes; this.buildBaseStringRepresentation(daideBytes);
    let remainingBytes = daideBytes;
    const [lead_token_obj, r0] = parse_bytes_ts(SingleTokenTs, remainingBytes);
    if (!lead_token_obj || lead_token_obj.getToken()?.toString() !== 'TME') throw new Error('Expected TME request');
    remainingBytes = r0;

    const [seconds_group_bytes, r1] = break_next_group_ts(remainingBytes);
    if (seconds_group_bytes) {
        const inner_seconds = strip_parentheses_ts(seconds_group_bytes);
        const [num_obj, r_num] = parse_bytes_ts(NumberTs, inner_seconds);
        if (!num_obj?.isValid) throw new Error("TME: Invalid number for seconds");
        if (r_num.length > 0) throw new Error("TME: Extra bytes in seconds group");
        this.seconds = num_obj.toInt();
        remainingBytes = r1;
    } // If no group, seconds remains null (for TME without params)
    if (remainingBytes.length > 0) throw new Error(`TME request malformed, ${remainingBytes.length} bytes remaining.`);
  }
}

export class DrawRequestTs extends DaideRequest {
  __type__ = "DrawRequest";
  powers: string[] = []; // Long power names
  constructor() { super(); }
  parseBytes(daideBytes: Uint8Array): void {
    this._bytes = daideBytes; this.buildBaseStringRepresentation(daideBytes);
    let remainingBytes = daideBytes;
    const [lead_token_obj, r0] = parse_bytes_ts(SingleTokenTs, remainingBytes);
    if (!lead_token_obj || lead_token_obj.getToken()?.toString() !== 'DRW') throw new Error('Expected DRW request');
    remainingBytes = r0;

    const [powers_group_bytes, r1] = break_next_group_ts(remainingBytes);
    if (powers_group_bytes) {
        let inner_powers = strip_parentheses_ts(powers_group_bytes);
        while(inner_powers.length > 0) {
            const [power_obj, r_power] = parse_bytes_ts(PowerTs, inner_powers);
            if (!power_obj?.isValid) throw new Error("DRW: Invalid power in list");
            this.powers.push(power_obj.toString());
            inner_powers = r_power;
        }
    }
    remainingBytes = r1;
    if (remainingBytes.length > 0) throw new Error(`DRW request malformed, ${remainingBytes.length} bytes remaining.`);
  }
}

export class SendMessageRequestTs extends DaideRequest {
  __type__ = "SendMessageRequest";
  parsedPhase: string = ''; // Optional turn
  powers: string[] = []; // List of long power names (recipients)
  message_bytes: Uint8Array = new Uint8Array(0); // Raw bytes of the inner message clause

  constructor() { super(); }
  parseBytes(daideBytes: Uint8Array): void {
    this._bytes = daideBytes; this.buildBaseStringRepresentation(daideBytes);
    let remainingBytes = daideBytes;

    const [lead_token_obj, r0] = parse_bytes_ts(SingleTokenTs, remainingBytes);
    if (!lead_token_obj || lead_token_obj.getToken()?.toString() !== 'SND') throw new Error('Expected SND request');
    remainingBytes = r0;

    const [turn_obj, r_turn] = parse_bytes_ts(TurnTs, remainingBytes, 'ignore');
    if (turn_obj?.isValid) {
        this.parsedPhase = turn_obj.toString();
        remainingBytes = r_turn;
    }

    const [powers_group_bytes, r_pg] = break_next_group_ts(remainingBytes);
    if (!powers_group_bytes) throw new Error("SND: Missing powers group");
    let inner_powers = strip_parentheses_ts(powers_group_bytes);
    while(inner_powers.length > 0) {
        const [power_obj, r_p] = parse_bytes_ts(PowerTs, inner_powers);
        if (!power_obj?.isValid) throw new Error("SND: Invalid power in list");
        this.powers.push(power_obj.toString());
        inner_powers = r_p;
    }
    if (this.powers.length === 0) throw new Error("SND: Expected at least one power in powers group");
    remainingBytes = r_pg;

    const [message_group_bytes, r_mg] = break_next_group_ts(remainingBytes);
    if (!message_group_bytes) throw new Error("SND: Missing message group");
    this.message_bytes = strip_parentheses_ts(message_group_bytes);
    remainingBytes = r_mg;

    if (remainingBytes.length > 0) throw new Error(`SND request malformed, ${remainingBytes.length} bytes remaining.`);
  }
}

// ... Stubs for NotRequest, AcceptRequest, RejectRequest, ParenthesisErrorRequest, SyntaxErrorRequest, AdminMessageRequest ...
export class NotRequestTs extends DaideRequest { __type__ = "NotRequest"; requestToNegate: DaideRequest | null = null; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class AcceptRequestTs extends DaideRequest { __type__ = "AcceptRequest"; response_bytes: Uint8Array = new Uint8Array(0); constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class RejectRequestTs extends DaideRequest { __type__ = "RejectRequest"; response_bytes: Uint8Array = new Uint8Array(0); constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class ParenthesisErrorRequestTs extends DaideRequest { __type__ = "ParenthesisErrorRequest"; message_bytes: Uint8Array = new Uint8Array(0); constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class SyntaxErrorRequestTs extends DaideRequest { __type__ = "SyntaxErrorRequest"; message_bytes: Uint8Array = new Uint8Array(0); constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }
export class AdminMessageRequestTs extends DaideRequest { __type__ = "AdminMessageRequest"; adm_message: string = ''; constructor() {super();} parseBytes(db: Uint8Array){this._bytes=db; this.buildBaseStringRepresentation(db);} }


// RequestBuilder Class
type DaideRequestConstructor = new (...args: any[]) => DaideRequest;
const REQUEST_CONSTRUCTOR_MAP_TS = new Map<string, DaideRequestConstructor>();

function bytesToKey(bytes: Uint8Array): string {
    return `${bytes[0]},${bytes[1]}`;
}

// Populate map (Token bytes are Uint8Array, convert to string key)
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.NME.toBytes()), NameRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.OBS.toBytes()), ObserverRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.IAM.toBytes()), IAmRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.HLO.toBytes()), HelloRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.MAP.toBytes()), MapRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.MDF.toBytes()), MapDefinitionRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.SCO.toBytes()), SupplyCentreOwnershipRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.NOW.toBytes()), CurrentPositionRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.HST.toBytes()), HistoryRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.SUB.toBytes()), SubmitOrdersRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.MIS.toBytes()), MissingOrdersRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.GOF.toBytes()), GoFlagRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.TME.toBytes()), TimeToDeadlineRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.DRW.toBytes()), DrawRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.SND.toBytes()), SendMessageRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.NOT.toBytes()), NotRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.YES.toBytes()), AcceptRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.REJ.toBytes()), RejectRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.PRN.toBytes()), ParenthesisErrorRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.HUH.toBytes()), SyntaxErrorRequestTs);
REQUEST_CONSTRUCTOR_MAP_TS.set(bytesToKey(daideTokens.ADM.toBytes()), AdminMessageRequestTs);


export class RequestBuilderTs {
  static fromBytes(daideBytes: Uint8Array, ...constructorArgs: any[]): DaideRequest | null {
    if (daideBytes.length < 2) return null;
    const initialTokenBytes = daideBytes.slice(0, 2);
    const key = bytesToKey(initialTokenBytes);

    const RequestClass = REQUEST_CONSTRUCTOR_MAP_TS.get(key);
    if (!RequestClass) {
      throw new Error(`RequestBuilderTs: Unable to find a constructor for token bytes ${key} (${new Token({from_bytes: initialTokenBytes}).toString()})`);
    }
    const requestInstance = new RequestClass(...constructorArgs);
    requestInstance.parseBytes(daideBytes); // Pass the full original bytes
    return requestInstance;
  }
}

// Aliases
export const NME = NameRequestTs;
export const OBS = ObserverRequestTs;
// ... Add all other aliases similarly
export const IAM = IAmRequestTs;
export const HLO = HelloRequestTs;
export const MAP = MapRequestTs;
export const MDF = MapDefinitionRequestTs;
export const SCO = SupplyCentreOwnershipRequestTs;
export const NOW = CurrentPositionRequestTs;
export const HST = HistoryRequestTs;
export const SUB = SubmitOrdersRequestTs;
export const MIS = MissingOrdersRequestTs;
export const GOF = GoFlagRequestTs;
export const TME = TimeToDeadlineRequestTs;
export const DRW = DrawRequestTs;
export const SND = SendMessageRequestTs;
export const NOT = NotRequestTs;
export const YES = AcceptRequestTs;
export const REJ = RejectRequestTs;
export const PRN = ParenthesisErrorRequestTs;
export const HUH = SyntaxErrorRequestTs;
export const ADM = AdminMessageRequestTs;
