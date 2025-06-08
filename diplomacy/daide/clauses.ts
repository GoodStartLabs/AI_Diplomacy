// diplomacy/daide/clauses.ts

import { Token, OPE_PAR, CLO_PAR, isIntegerToken, isAsciiToken, CTO, MTO, DSB, REM } from './tokens'; // Assuming tokens.ts is available

// Logger
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

export type OnErrorAction = 'raise' | 'warn' | 'ignore';

// Helper Functions
export function break_next_group_ts(daideBytes: Uint8Array): [Uint8Array | null, Uint8Array] {
  if (!daideBytes || daideBytes.length < 2) {
    return [null, daideBytes];
  }

  if (daideBytes[0] !== OPE_PAR.toBytes()[0] || daideBytes[1] !== OPE_PAR.toBytes()[1]) {
    return [null, daideBytes];
  }

  let pos = 0;
  let parentheses_level = 0;
  while (pos < daideBytes.length) {
    if (daideBytes[pos] === OPE_PAR.toBytes()[0] && daideBytes[pos+1] === OPE_PAR.toBytes()[1]) {
      parentheses_level++;
    } else if (daideBytes[pos] === CLO_PAR.toBytes()[0] && daideBytes[pos+1] === CLO_PAR.toBytes()[1]) {
      parentheses_level--;
    }
    if (parentheses_level <= 0) {
      break;
    }
    if (pos + 2 >= daideBytes.length) {
        pos = 0;
        break;
    }
    pos += 2;
  }

  if (pos === 0 && parentheses_level !== 0) {
      return [null, daideBytes];
  }
   if (parentheses_level > 0 && pos + 2 >= daideBytes.length) {
      logger.warn("Mismatched parentheses in DAIDE bytes for group breaking.");
      return [null, daideBytes];
  }


  return [daideBytes.slice(0, pos + 2), daideBytes.slice(pos + 2)];
}

export function add_parentheses_ts(daideBytes: Uint8Array): Uint8Array {
  if (!daideBytes || daideBytes.length === 0) {
    return daideBytes;
  }
  const opeParBytes = OPE_PAR.toBytes();
  const cloParBytes = CLO_PAR.toBytes();
  const result = new Uint8Array(opeParBytes.length + daideBytes.length + cloParBytes.length);
  result.set(opeParBytes, 0);
  result.set(daideBytes, opeParBytes.length);
  result.set(cloParBytes, opeParBytes.length + daideBytes.length);
  return result;
}

export function strip_parentheses_ts(daideBytes: Uint8Array): Uint8Array {
  const opeParBytes = OPE_PAR.toBytes();
  const cloParBytes = CLO_PAR.toBytes();
  if (daideBytes.length < 4 ||
      daideBytes[0] !== opeParBytes[0] || daideBytes[1] !== opeParBytes[1] ||
      daideBytes[daideBytes.length - 2] !== cloParBytes[0] || daideBytes[daideBytes.length - 1] !== cloParBytes[1]) {
    throw new Error('Expected bytes to start with "(" and end with ")"');
  }
  return daideBytes.slice(2, -2);
}

// AbstractClause Class
export abstract class AbstractClauseTs {
  protected _is_valid: boolean = true;

  get isValid(): boolean {
    return this._is_valid;
  }

  abstract toBytes(): Uint8Array;
  abstract fromBytes(daideBytes: Uint8Array, onError?: OnErrorAction): Uint8Array;
  abstract fromString(str: string, onError?: OnErrorAction): void;

  protected error(onError: OnErrorAction = 'raise', message: string = ''): void {
    this._is_valid = false;
    if (onError === 'raise') {
      throw new Error(message || "Clause parsing/validation error.");
    }
    if (onError === 'warn') {
      logger.warn(message || "Clause parsing/validation error.");
    }
  }
}

export function parse_bytes_ts<T extends AbstractClauseTs>(
    ClauseClass: new () => T,
    daideBytes: Uint8Array,
    onError: OnErrorAction = 'raise'
): [T | null, Uint8Array] {
    const clause = new ClauseClass();
    const remainingBytes = clause.fromBytes(daideBytes, onError);
    if (!clause.isValid) {
        return [null, daideBytes]; // Return original bytes if clause is invalid and parsing failed early
    }
    return [clause, remainingBytes];
}

export function parse_string_ts<T extends AbstractClauseTs>(
    ClauseClass: new () => T,
    str: string,
    onError: OnErrorAction = 'raise'
): T | null {
    const clause = new ClauseClass();
    clause.fromString(str, onError);
    if (!clause.isValid) {
        return null;
    }
    return clause;
}

export class SingleTokenTs extends AbstractClauseTs {
  protected _token: Token | null = null;

  toBytes(): Uint8Array {
    if (!this._token) return new Uint8Array(0);
    return this._token.toBytes();
  }
  toString(): string {
    return this._token ? this._token.toString() : '';
  }
  getToken(): Token | null { return this._token; }

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    if (daideBytes.length < 2) { this.error(onError, 'At least 2 bytes are required for SingleToken.fromBytes.'); return daideBytes; }
    const token_bytes = daideBytes.slice(0, 2);
    const remaining_bytes = daideBytes.slice(2);
    try { this._token = new Token({ from_bytes: token_bytes }); this._is_valid = true; }
    catch (e: any) { this.error(onError, e.message); return daideBytes; }
    return remaining_bytes;
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    if (!str) { this.error(onError, 'Input string cannot be empty for SingleToken.fromString.'); return; }
    try { this._token = new Token({ from_str: str }); this._is_valid = true; }
    catch (e: any) { this.error(onError, e.message); }
  }
}

export class PowerTs extends SingleTokenTs {
  private static readonly _alias_from_bytes: Record<string, string> = {
    'AUS': 'AUSTRIA', 'ENG': 'ENGLAND', 'FRA': 'FRANCE', 'GER': 'GERMANY',
    'ITA': 'ITALY', 'RUS': 'RUSSIA', 'TUR': 'TURKEY'
  };
  private static readonly _alias_from_string: Record<string, string> =
    Object.fromEntries(Object.entries(PowerTs._alias_from_bytes).map(([k, v]) => [v, k]));
  private _power_long_name: string = '';

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    const remainingBytes = super.fromBytes(daideBytes, onError);
    if (this.isValid && this._token) {
      this._power_long_name = PowerTs._alias_from_bytes[this._token.toString()] || this._token.toString();
    }
    return remainingBytes;
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    const daidePowerStr = PowerTs._alias_from_string[str.toUpperCase()] || str;
    super.fromString(daidePowerStr, onError);
    if (this.isValid) this._power_long_name = str;
  }
  toString(): string { return this._power_long_name || (this._token ? this._token.toString() : ''); }
  get shortName(): string { return this._token ? this._token.toString() : ''; }
}

export class StringTs extends AbstractClauseTs {
  private _value: string = '';
  private _raw_bytes: Uint8Array = new Uint8Array(0);

  toBytes(): Uint8Array { return this._raw_bytes; }
  toString(): string { return this._value; }

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    const [str_group_bytes, remaining_bytes] = break_next_group_ts(daideBytes);
    if (!str_group_bytes) { this.error(onError, 'StringTs: No parenthesized group found.'); return daideBytes; }
    this._raw_bytes = str_group_bytes;
    const inner_bytes = strip_parentheses_ts(str_group_bytes);
    let parsed_string = "";
    for (let i = 0; i < inner_bytes.length; i += 2) {
      if (i + 1 >= inner_bytes.length) { this.error(onError, 'StringTs: Malformed byte sequence.'); return daideBytes; }
      try {
        const char_token = new Token({ from_bytes: inner_bytes.slice(i, i + 2) });
        if (!isAsciiToken(char_token)) { this.error(onError, `StringTs: Expected ASCII token, got ${char_token.toString()}`); return daideBytes; }
        parsed_string += char_token.toString();
      } catch (e:any) { this.error(onError, `StringTs: Error parsing char token: ${e.message}`); return daideBytes; }
    }
    this._value = parsed_string; this._is_valid = true;
    return remaining_bytes;
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    this._value = str;
    const byteTokens: Uint8Array[] = [];
    for (let i = 0; i < str.length; i++) {
      try { byteTokens.push(new Token({ from_str: str[i] }).toBytes()); }
      catch (e:any) { this.error(onError, `StringTs: Error converting char '${str[i]}': ${e.message}`); return; }
    }
    let totalLength = 0; byteTokens.forEach(bt => totalLength += bt.length);
    const combinedBytes = new Uint8Array(totalLength);
    let offset = 0; byteTokens.forEach(bt => { combinedBytes.set(bt, offset); offset += bt.length; });
    this._raw_bytes = add_parentheses_ts(combinedBytes); this._is_valid = true;
  }
}

export class NumberTs extends AbstractClauseTs {
  private _value: number = 0;
  private _token: Token | null = null;

  toBytes(): Uint8Array { return this._token ? this._token.toBytes() : new Uint8Array(0); }
  toString(): string { return String(this._value); }
  toInt(): number { return this._value; }

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    if (daideBytes.length < 2) { this.error(onError, 'NumberTs: Expected 2 bytes for number token.'); return daideBytes; }
    const number_bytes = daideBytes.slice(0, 2);
    const remaining_bytes = daideBytes.slice(2);
    try {
      const token = new Token({ from_bytes: number_bytes });
      if (!isIntegerToken(token) || token.toInt() === null) { this.error(onError, `NumberTs: Not a valid integer token: ${token.toString()}`); return daideBytes; }
      this._token = token; this._value = token.toInt()!; this._is_valid = true;
    } catch (e: any) { this.error(onError, e.message); return daideBytes; }
    return remaining_bytes;
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    try {
      const num_val = parseInt(str, 10);
      if (isNaN(num_val)) { this.error(onError, `NumberTs: Invalid number string: "${str}"`); return; }
      this._token = new Token({ from_int: num_val }); this._value = num_val; this._is_valid = true;
    } catch (e: any) { this.error(onError, e.message); }
  }
}

export class ProvinceTs extends AbstractClauseTs {
  private _province_str: string = '';
  private _raw_bytes: Uint8Array = new Uint8Array(0);
  private static readonly _alias_from_bytes: Record<string, string> = {'ECS': '/EC', 'NCS': '/NC', 'SCS': '/SC', 'WCS': '/WC', 'NEC': '/NEC', 'NWC': '/NWC', 'SEC': '/SEC', 'SWC': '/SWC', 'ECH': 'ENG', 'GOB': 'BOT', 'GOL': 'LYO'};
  private static readonly _alias_from_string: Record<string, string> = Object.fromEntries(Object.entries(ProvinceTs._alias_from_bytes).map(([k, v]) => [v, k]));

  toBytes(): Uint8Array { return this._raw_bytes; }
  toString(): string { return this._province_str; }

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    const [group, remaining] = break_next_group_ts(daideBytes);
    if (group) { // Coasted: (STP NCS)
      this._raw_bytes = group;
      const inner = strip_parentheses_ts(group);
      const [prov_obj, r1] = parse_bytes_ts(SingleTokenTs, inner, onError);
      if (!prov_obj?.isValid) { this.error(onError,"ProvTs: Invalid province in coasted."); return daideBytes;}
      const [coast_obj, r2] = parse_bytes_ts(SingleTokenTs, r1, onError);
      if (!coast_obj?.isValid) { this.error(onError,"ProvTs: Invalid coast in coasted."); return daideBytes;}
      if (r2.length > 0) { this.error(onError,"ProvTs: Extra bytes in coasted province."); return daideBytes;}
      const prov_s = prov_obj.toString(), coast_s = coast_obj.toString();
      this._province_str = (ProvinceTs._alias_from_bytes[prov_s] || prov_s) + (ProvinceTs._alias_from_bytes[coast_s] || coast_s);
      this._is_valid = true; return remaining;
    } else { // Non-coasted: ADR
      if (daideBytes.length < 2) { this.error(onError, "ProvTs: Not enough bytes for non-coasted."); return daideBytes; }
      const [prov_obj, new_remaining] = parse_bytes_ts(SingleTokenTs, daideBytes, onError);
      if (!prov_obj?.isValid) { this.error(onError,"ProvTs: Invalid token for non-coasted."); return daideBytes;}
      this._raw_bytes = prov_obj.toBytes();
      const prov_s = prov_obj.toString();
      this._province_str = ProvinceTs._alias_from_bytes[prov_s] || prov_s;
      this._is_valid = true; return new_remaining;
    }
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    this._province_str = str;
    let prov_part = str, coast_part_lookup: string | null = null;
    if (str.includes('/')) { [prov_part, coast_part_lookup] = str.split('/'); coast_part_lookup = `/${coast_part_lookup}`; }
    const daide_prov_s = ProvinceTs._alias_from_string[prov_part] || prov_part;
    try {
      const prov_token = new Token({ from_str: daide_prov_s });
      if (coast_part_lookup) {
        const daide_coast_s = ProvinceTs._alias_from_string[coast_part_lookup];
        if (!daide_coast_s) { this.error(onError, `ProvTs: Unknown coast: "${coast_part_lookup}"`); return; }
        const coast_token = new Token({ from_str: daide_coast_s });
        this._raw_bytes = add_parentheses_ts(new Uint8Array([...prov_token.toBytes(), ...coast_token.toBytes()]));
      } else { this._raw_bytes = prov_token.toBytes(); }
      this._is_valid = true;
    } catch (e:any) { this.error(onError, e.message); }
  }
}

export class TurnTs extends AbstractClauseTs {
  private _turn_str: string = '';
  private _raw_bytes: Uint8Array = new Uint8Array(0);
  private static readonly _alias_from_bytes: Record<string, string> = {'AUT': 'F.R', 'FAL': 'F.M', 'SPR': 'S.M', 'SUM': 'S.R', 'WIN': 'W.A'};
  private static readonly _alias_from_string: Record<string, string> = Object.fromEntries(Object.entries(TurnTs._alias_from_bytes).map(([k, v]) => [v, k]));

  toBytes(): Uint8Array { return this._raw_bytes; }
  toString(): string { return this._turn_str; }

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    const [group, remaining] = break_next_group_ts(daideBytes);
    if (!group) { this.error(onError, "TurnTs: No parenthesized group."); return daideBytes; }
    this._raw_bytes = group; const inner = strip_parentheses_ts(group);
    const [season_obj, r1] = parse_bytes_ts(SingleTokenTs, inner, onError);
    if (!season_obj?.isValid) { this.error(onError,"TurnTs: Invalid season."); return daideBytes; }
    const [year_obj, r2] = parse_bytes_ts(NumberTs, r1, onError);
    if (!year_obj?.isValid) { this.error(onError,"TurnTs: Invalid year."); return daideBytes; }
    if (r2.length > 0) { this.error(onError,"TurnTs: Extra bytes."); return daideBytes; }
    const season_s = season_obj.toString(), year_i = year_obj.toInt();
    const season_alias = TurnTs._alias_from_bytes[season_s] || season_s;
    this._turn_str = `${season_alias[0]}${String(year_i).slice(-2)}${season_alias[season_alias.length -1]}`;
    this._is_valid = true; return remaining;
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    this._turn_str = str;
    if (str.length < 4) { this.error(onError, `TurnTs: String too short: "${str}"`); return; }
    const season_key = `${str[0].toUpperCase()}.${str[str.length-1].toUpperCase()}`;
    const year_s = str.substring(1, str.length - 1);
    const daide_season_s = TurnTs._alias_from_string[season_key];
    if (!daide_season_s) { this.error(onError, `TurnTs: Unknown season: "${season_key}"`); return; }
    let full_year = parseInt(year_s, 10);
    if (isNaN(full_year)) { this.error(onError, `TurnTs: Invalid year string: "${year_s}"`); return; }
    if (full_year < 100) full_year += 1900;
    try {
      const season_token = new Token({ from_str: daide_season_s });
      const year_token = new Token({ from_int: full_year });
      this._raw_bytes = add_parentheses_ts(new Uint8Array([...season_token.toBytes(), ...year_token.toBytes()]));
      this._is_valid = true;
    } catch (e:any) { this.error(onError, e.message); }
  }
}

export class UnitTypeTs extends SingleTokenTs {
  private static readonly _alias_from_bytes: Record<string, string> = { 'AMY': 'A', 'FLT': 'F' };
  private static readonly _alias_from_string: Record<string, string> = { 'A': 'AMY', 'F': 'FLT' };
  private _unit_type_char: string = '';

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    const rem = super.fromBytes(daideBytes, onError);
    if (this.isValid && this._token) this._unit_type_char = UnitTypeTs._alias_from_bytes[this._token.toString()] || this._token.toString();
    return rem;
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    const upperS = str.toUpperCase();
    const daide_s = UnitTypeTs._alias_from_string[upperS] || upperS;
    super.fromString(daide_s, onError);
    if (this.isValid) {
      this._unit_type_char = upperS;
      if (!UnitTypeTs._alias_from_string[upperS] && upperS !== "AMY" && upperS !== "FLT") this.error(onError, `UnitTypeTs: Unknown: "${str}"`);
    }
  }
  toString(): string { return this._unit_type_char || (this._token ? UnitTypeTs._alias_from_bytes[this._token.toString()] || this._token.toString() : ''); }
  get daideTokenString(): string { return this._token ? this._token.toString() : ''; }
}

export class UnitTs extends AbstractClauseTs {
  private _unit_str: string = '';
  power: PowerTs | null = null;
  unit_type: UnitTypeTs | null = null;
  province: ProvinceTs | null = null;
  private _raw_bytes: Uint8Array = new Uint8Array(0);
  private static readonly UNKNOWN_POWER_DAIDE_STR = 'UNO';

  get power_name(): string | null { return this.power ? this.power.toString() : null; } // Long name
  get unitTypeChar(): string | null { return this.unit_type ? this.unit_type.toString() : null; } // 'A' or 'F'
  get provinceName(): string | null { return this.province ? this.province.toString() : null; }

  toBytes(): Uint8Array { return this._raw_bytes; }
  toString(): string { return this._unit_str; }

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    const [group, rem] = break_next_group_ts(daideBytes);
    if (!group) { this.error(onError, "UnitTs: No parenthesized group."); return daideBytes; }
    this._raw_bytes = group; let inner = strip_parentheses_ts(group);
    let p_obj, ut_obj, prov_obj;
    [p_obj, inner] = parse_bytes_ts(PowerTs, inner, onError);
    if (!p_obj?.isValid) { this.error(onError,"UnitTs: Invalid power."); return daideBytes; } this.power = p_obj;
    [ut_obj, inner] = parse_bytes_ts(UnitTypeTs, inner, onError);
    if (!ut_obj?.isValid) { this.error(onError,"UnitTs: Invalid unit type."); return daideBytes; } this.unit_type = ut_obj;
    [prov_obj, inner] = parse_bytes_ts(ProvinceTs, inner, onError);
    if (!prov_obj?.isValid) { this.error(onError,"UnitTs: Invalid province."); return daideBytes; } this.province = prov_obj;
    if (inner.length > 0) { this.error(onError,"UnitTs: Extra bytes."); return daideBytes; }
    this._unit_str = `${this.unit_type.toString()} ${this.province.toString()}`;
    if (this.power.shortName !== UnitTs.UNKNOWN_POWER_DAIDE_STR) this._unit_str = `${this.power.toString()} ${this._unit_str}`;
    this._is_valid = true; return rem;
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    const words = str.trim().split(/\s+/);
    let p_s, ut_s, prov_s;
    if (words.length === 2) { p_s = UnitTs.UNKNOWN_POWER_DAIDE_STR; [ut_s, prov_s] = words; }
    else if (words.length === 3) { [p_s, ut_s, prov_s] = words; }
    else { this.error(onError, `UnitTs: Expected 2 or 3 words. Got: "${str}"`); return; }
    this._unit_str = str; // Store original
    try {
      this.power = parse_string_ts(PowerTs, p_s, onError);
      this.unit_type = parse_string_ts(UnitTypeTs, ut_s, onError);
      this.province = parse_string_ts(ProvinceTs, prov_s, onError);
      if (!this.power?.isValid || !this.unit_type?.isValid || !this.province?.isValid) { this.error(onError, `UnitTs: Invalid component in "${str}"`); return; }
      this._raw_bytes = add_parentheses_ts(new Uint8Array([...this.power.toBytes(), ...this.unit_type.toBytes(), ...this.province.toBytes()]));
      this._is_valid = true;
    } catch (e:any) { this.error(onError, e.message); }
  }
}

export class OrderTypeTs extends SingleTokenTs {
  private static readonly _alias_from_bytes: Record<string, string> = {'HLD': 'H', 'MTO': '-', 'SUP': 'S', 'CVY': 'C', 'CTO': '-', 'VIA': 'VIA', 'RTO': 'R', 'DSB': 'D', 'BLD': 'B', 'REM': 'D', 'WVE': 'WAIVE'};
  private static readonly _alias_from_string: Record<string, string> = {'H': 'HLD', '-': 'MTO', 'S': 'SUP', 'C': 'CVY', 'R': 'RTO', 'D': 'REM', 'B': 'BLD', 'WAIVE': 'WVE', 'VIA': 'VIA'}; // Note: '-' maps to MTO, CTO handled by context. 'D' maps to REM, DSB by context.
  private _order_type_char: string = '';

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    const rem = super.fromBytes(daideBytes, onError);
    if (this.isValid && this._token) this._order_type_char = OrderTypeTs._alias_from_bytes[this._token.toString()] || this._token.toString();
    return rem;
  }
  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    const upperS = str.toUpperCase();
    const daide_s = OrderTypeTs._alias_from_string[upperS] || upperS;
    super.fromString(daide_s, onError);
    if (this.isValid) {
      this._order_type_char = upperS;
      if (!OrderTypeTs._alias_from_string[upperS] && !OrderTypeTs._alias_from_bytes[upperS /* check if DAIDE token passed directly */]) {
           // Check if `upperS` itself is a value in _alias_from_bytes (i.e. a DAIDE token string like "HLD")
          const isDaideToken = Object.values(OrderTypeTs._alias_from_bytes).includes(upperS) || Object.keys(OrderTypeTs._alias_from_bytes).includes(upperS);
          if (!isDaideToken) this.error(onError, `OrderTypeTs: Unknown: "${str}"`);
      }
    }
  }
  toString(): string { return this._order_type_char || (this._token ? OrderTypeTs._alias_from_bytes[this._token.toString()] || this._token.toString() : ''); }
  get daideTokenString(): string { return this._token ? this._token.toString() : ''; }
}

export class OrderTs extends AbstractClauseTs {
  private _order_str: string = '';
  power_name: string | null = null; // Long name
  private _raw_bytes: Uint8Array = new Uint8Array(0);

  // Components of the order
  unit: UnitTs | null = null;
  powerTokenForWaive: PowerTs | null = null; // Only for (AUS WVE)
  order_type: OrderTypeTs | null = null;
  first_province: ProvinceTs | null = null;
  second_province: ProvinceTs | null = null; // For convoy routes (VIA)
  first_unit_clause: UnitTs | null = null; // For support/convoy target unit
  second_order_type: OrderTypeTs | null = null; // For S ... MTO ... or C ... CTO ...

  toBytes(): Uint8Array { return this._raw_bytes; }
  toString(): string { return this._order_str; }

  fromBytes(daideBytes: Uint8Array, onError: OnErrorAction = 'raise'): Uint8Array {
    const [group, rem] = break_next_group_ts(daideBytes);
    if (!group) { this.error(onError, "OrderTs: No parenthesized group."); return daideBytes; }
    this._raw_bytes = group; let inner = strip_parentheses_ts(group);

    // Try parsing (UNIT ORDER_TYPE ...)
    let p_unit, p_order_type, p_first_prov, p_second_prov, p_first_unit, p_second_order_type;

    [p_unit, inner] = parse_bytes_ts(UnitTs, inner, 'ignore');
    if (p_unit && p_unit.isValid) {
        this.unit = p_unit;
        this.power_name = p_unit.power_name;

        [p_order_type, inner] = parse_bytes_ts(OrderTypeTs, inner, onError);
        if (!p_order_type?.isValid) { this.error(onError, "OrderTs: Invalid order type after unit."); return daideBytes; }
        this.order_type = p_order_type;
        const order_type_s = this.order_type.toString(); // This is 'H', '-', 'S', 'C', 'R', 'D', 'B'

        if (order_type_s === '-' || order_type_s === 'R' || order_type_s === 'B') { // MTO, RTO, BLD
            if (inner.length > 0) { // These might have a province
                [p_first_prov, inner] = parse_bytes_ts(ProvinceTs, inner, 'ignore');
                if (p_first_prov?.isValid) this.first_province = p_first_prov;
                else if (order_type_s === '-' || order_type_s === 'R') { // MTO/RTO require province
                     this.error(onError, `OrderTs: ${order_type_s} requires a province.`); return daideBytes;
                }
            } else if (order_type_s === '-' || order_type_s === 'R') { // MTO/RTO require province
                 this.error(onError, `OrderTs: ${order_type_s} requires a province, but no bytes left.`); return daideBytes;
            }
             // Check for VIA for MTO (which is CTO)
            if (this.order_type.daideTokenString === 'MTO' && inner.length > 0) { // Check if it was actually CTO
                const [via_check, via_rem] = parse_bytes_ts(OrderTypeTs, inner, 'ignore');
                if (via_check?.isValid && via_check.daideTokenString === 'VIA') {
                    this.order_type = parse_string_ts(OrderTypeTs, 'CTO')!; // Change MTO to CTO conceptually
                    this.second_order_type = via_check; // This is VIA
                    // The provinces for VIA (A B C VIA ( D E F )) are not parsed here, they are part of the message structure typically
                    // This simplified parsing assumes VIA is just a flag after first province for CTO.
                    // The Python example `FRANCE A IRI - MAO VIA` implies VIA is like an order type.
                    // And `bytes(Token(tokens.CTO))` for `A IRI - MAO VIA`.
                    // `( (FRA AMY IRI) CTO MAO VIA )`
                    // Let's assume 'VIA' token follows the first province for CTO.
                    inner = via_rem;
                }
            }

        } else if (order_type_s === 'S') { // SUP
            [p_first_unit, inner] = parse_bytes_ts(UnitTs, inner, onError);
            if (!p_first_unit?.isValid) { this.error(onError,"OrderTs: Support needs a target unit."); return daideBytes;}
            this.first_unit_clause = p_first_unit;
            // Optional second part: ( (FRA AMY PAR) SUP (ENG FLT ECH) MTO ENG )
            if (inner.length > 0) {
                [p_second_order_type, inner] = parse_bytes_ts(OrderTypeTs, inner, 'ignore');
                if (p_second_order_type?.isValid && p_second_order_type.toString() === '-') { // MTO
                    this.second_order_type = p_second_order_type;
                    [p_first_prov, inner] = parse_bytes_ts(ProvinceTs, inner, onError);
                    if(!p_first_prov?.isValid) { this.error(onError,"OrderTs: Support-Move needs target province."); return daideBytes;}
                    this.first_province = p_first_prov;
                } else if (p_second_order_type?.isValid) { // Some other token, unexpected
                     this.error(onError,"OrderTs: Unexpected token after S (UNIT)."); return daideBytes;
                }
            }
        } else if (order_type_s === 'C') { // CVY
            [p_first_unit, inner] = parse_bytes_ts(UnitTs, inner, onError); // Army to convoy
            if (!p_first_unit?.isValid) { this.error(onError,"OrderTs: Convoy needs unit to convoy."); return daideBytes;}
            this.first_unit_clause = p_first_unit;

            [p_second_order_type, inner] = parse_bytes_ts(OrderTypeTs, inner, onError); // Should be MTO (CTO in DAIDE)
            if (!p_second_order_type?.isValid || p_second_order_type.daideTokenString !== 'MTO') { // Represented as MTO in string, but becomes CTO
                this.error(onError,"OrderTs: Convoy needs MTO for convoyed unit's move."); return daideBytes;
            }
            this.second_order_type = new OrderTypeTs(); // Conceptually CTO
            this.second_order_type.fromString('CTO', onError);


            [p_first_prov, inner] = parse_bytes_ts(ProvinceTs, inner, onError); // Destination
            if(!p_first_prov?.isValid) { this.error(onError,"OrderTs: Convoy needs destination province."); return daideBytes;}
            this.first_province = p_first_prov;
        }
        // HLD, DSB, WVE (WVE handled by powerTokenForWaive path) do not take more args here.
    } else { // Try (POWER WVE)
        [p_order_type, inner] = parse_bytes_ts(OrderTypeTs, inner, onError); // This should be WVE
        if (p_order_type?.isValid && p_order_type.daideTokenString === 'WVE') {
            const [power_obj, r1] = parse_bytes_ts(PowerTs, strip_parentheses_ts(group).slice(0,2), 'ignore'); // Try parsing first element as Power
            if(power_obj?.isValid) {
                this.powerTokenForWaive = power_obj;
                this.order_type = p_order_type;
                this.power_name = this.powerTokenForWaive.toString();
                inner = r1.slice(p_order_type.toBytes().length); // Adjust inner based on what was consumed
            } else {
                 this.error(onError, "OrderTs: WVE order must be preceded by a Power token."); return daideBytes;
            }
        } else {
            this.error(onError, "OrderTs: Invalid structure. Expected (UNIT ...) or (POWER WVE)."); return daideBytes;
        }
    }

    if (inner.length > 0) { this.error(onError,`OrderTs: Extra bytes after parsing: ${inner.length}`); return daideBytes; }
    this._reconstruct_str();
    this._is_valid = true; return rem;
  }

  private _reconstruct_str(): void {
    if (this.powerTokenForWaive && this.order_type) { // (FRA WVE)
        this._order_str = `${this.powerTokenForWaive.toString()} ${this.order_type.toString()}`;
    } else if (this.unit && this.order_type) {
        let parts = [this.unit.toString(), this.order_type.toString()];
        if (this.first_unit_clause) parts.push(this.first_unit_clause.toString());
        if (this.second_order_type) parts.push(this.second_order_type.toString()); // This is MTO/CTO or VIA
        if (this.first_province) parts.push(this.first_province.toString());
        // Note: VIA for CTO might need special handling if it has more provinces
        this._order_str = parts.join(" ");
    } else {
        this._order_str = "Invalid/Unparsed Order";
    }
  }

  fromString(str: string, onError: OnErrorAction = 'raise'): void {
    this.error(onError, "OrderTs.fromString is not implemented due to complexity of parsing various order formats.");
    // This would require a full order parser similar to diplomacy.standard_order_parser
  }
}

export interface OrderSplit {
    unit: string; // e.g. "FRA A PAR" or "A PAR"
    order_type: string; // e.g. "H", "-", "S", "C", "R", "D", "B", "WAIVE"
    destination?: string | null; // e.g. "PIC"
    supported_unit?: string | null; // e.g. "ENG F ECH" (unit being supported/convoyed)
    support_order_type?: string | null; // If support is for a move, this is "-"
    via_flag?: string | null; // "VIA"
    length: number; // Helper to know number of main components for Python's len(order_split)
}

export function parse_order_to_bytes_ts(phase_type: string, order_split: OrderSplit): Uint8Array {
    const buffer_clauses: AbstractClauseTs[] = [];

    if (order_split.order_type.toUpperCase() === 'WAIVE' && order_split.unit.split(' ').length === 1) { // e.g. unit="FRA", order_type="WAIVE"
        const power = parse_string_ts(PowerTs, order_split.unit, 'raise');
        const order_type_token = parse_string_ts(OrderTypeTs, order_split.order_type, 'raise');
        if (!power || !order_type_token) throw new Error("Invalid WAIVE order parts");
        buffer_clauses.push(power, order_type_token);
    } else {
        const unit = parse_string_ts(UnitTs, order_split.unit, 'raise');
        if (!unit) throw new Error("Invalid unit in order_split");
        buffer_clauses.push(unit);

        let daide_order_type_str = order_split.order_type;
        if (order_split.order_type === '-') {
            daide_order_type_str = order_split.via_flag ? 'CTO' : 'MTO';
        } else if (order_split.order_type === 'D') {
            daide_order_type_str = phase_type === 'R' ? 'DSB' : 'REM';
        }
        const order_type = parse_string_ts(OrderTypeTs, daide_order_type_str, 'raise');
        if (!order_type) throw new Error(`Invalid order_type: ${daide_order_type_str}`);
        buffer_clauses.push(order_type);

        if (order_split.supported_unit) {
            const supported_unit_clause = parse_string_ts(UnitTs, order_split.supported_unit, 'raise');
            if (!supported_unit_clause) throw new Error("Invalid supported_unit");
            buffer_clauses.push(supported_unit_clause);
        }
        if (order_split.support_order_type) { // e.g. for S ... MTO ...
            const support_action_type = parse_string_ts(OrderTypeTs, order_split.support_order_type, 'raise');
            if(!support_action_type) throw new Error("Invalid support_order_type");
            buffer_clauses.push(support_action_type);
        }
        if (order_split.destination) {
            const dest_prov = parse_string_ts(ProvinceTs, order_split.destination, 'raise');
            if(!dest_prov) throw new Error("Invalid destination province");
            buffer_clauses.push(dest_prov);
        }
        if (order_split.via_flag) { // This is 'VIA' token itself
            const via_token = parse_string_ts(OrderTypeTs, order_split.via_flag, 'raise');
            if(!via_token) throw new Error("Invalid VIA flag");
            buffer_clauses.push(via_token);
        }
    }

    const byteArrays = buffer_clauses.map(clause => clause.toBytes());
    let totalLength = 0;
    byteArrays.forEach(ba => totalLength += ba.length);
    const combinedBytes = new Uint8Array(totalLength);
    let offset = 0;
    byteArrays.forEach(ba => {
        combinedBytes.set(ba, offset);
        offset += ba.length;
    });
    return add_parentheses_ts(combinedBytes);
}
