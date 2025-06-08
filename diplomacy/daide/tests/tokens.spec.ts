// diplomacy/daide/tests/tokens.spec.ts

import {
    Token,
    // Import all known tokens that were registered
    // Powers
    AUS, ENG, FRA, GER, ITA, RUS, TUR,
    // Units
    AMY, FLT,
    // Orders
    CTO, CVY, HLD, MTO, SUP, VIA, DSB, RTO, BLD, REM, WVE,
    // Order Notes (Results)
    SUC, BNC, CUT, DSR, FLD as RESULT_FLD, // FLD is also an order note token, alias to avoid clash
    NSO, RET as RESULT_RET, // RET is also a command token
    // Order Notes (THX)
    MBV, BPR, CST, ESC, FAR, HSC, NAS, NMB, NMR, NRN, NRS, NSA, NSC, NSF, NSP, NSU, NVR, NYU, YSC,
    // Coasts
    NCS, NEC, ECS, SEC, SCS, SWC, WCS, NWC,
    // Seasons
    SPR, SUM, FAL, AUT, WIN,
    // Commands
    CCD, DRW, FRM, GOF, HLO, HST, HUH, IAM, LOD, MAP, MDF, MIS, NME, NOT, NOW, OBS, OFF, ORD, OUT, PRN, REJ, SCO, SLO, SND, SUB, SVE, THX, TME, YES, ADM, SMR,
    // Parameters
    AOA, BTL, ERR, LVL, MRT, MTL, NPB, NPR, PDA, PTL, RTL, UNO, DSD,
    // Press
    ALY, AND, BWX, DMZ, ELS, EXP, FCT, FOR, FWD, HOW, IDK, IFF, INS, OCC, ORR, PCE, POB, PRP, QRY, SCD, SRY, SUG, THK, THN, TRY, VSS, WHT, WHY, XDO, XOY, YDO, CHO, BCC, UNT, NAR, CCL,
    // Provinces (a selection, as there are many)
    ADR, AEG, ALB, ANK, APU, ARM, BAL, BAR, BEL, BER, BLA, BOH, BRE, BUD, BUL, BUR, CLY, CON, DEN, EAS, ECH, EDI, FIN, GAL, GAS, GOB, GOL, GRE, HEL, HOL, ION, IRI, KIE, LON, LVN, LVP, MAO, MAR, MOS, MUN, NAF, NAO, NAP, NTH, NWG, NWY, PAR, PIC, PIE, POR, PRU, ROM, RUH, RUM, SER, SEV, SIL, SKA, SMY, SPA, STP, SWE, SYR, TRI, TUN, TUS, TYR, TYS, UKR, VEN, VIE, WAL, WAR, WES, YOR,
    // Symbols
    OPE_PAR, CLO_PAR,
} from '../tokens'; // Adjust path as necessary

// This maps the string name from Python's ExpectedTokens enum to the imported Token object and its expected byte value.
// The string name helps in identifying the token during test failures.
const expectedTokenData: Array<{ name: string; tokenObj: Token; expectedBytesTuple: [number, number]; expectedStr: string }> = [
  // Powers
  { name: "TOKEN_POWER_AUS", tokenObj: AUS, expectedBytesTuple: [0x41, 0x00], expectedStr: "AUS" },
  { name: "TOKEN_POWER_ENG", tokenObj: ENG, expectedBytesTuple: [0x41, 0x01], expectedStr: "ENG" },
  { name: "TOKEN_POWER_FRA", tokenObj: FRA, expectedBytesTuple: [0x41, 0x02], expectedStr: "FRA" },
  { name: "TOKEN_POWER_GER", tokenObj: GER, expectedBytesTuple: [0x41, 0x03], expectedStr: "GER" },
  { name: "TOKEN_POWER_ITA", tokenObj: ITA, expectedBytesTuple: [0x41, 0x04], expectedStr: "ITA" },
  { name: "TOKEN_POWER_RUS", tokenObj: RUS, expectedBytesTuple: [0x41, 0x05], expectedStr: "RUS" },
  { name: "TOKEN_POWER_TUR", tokenObj: TUR, expectedBytesTuple: [0x41, 0x06], expectedStr: "TUR" },

  // Units
  { name: "TOKEN_UNIT_AMY", tokenObj: AMY, expectedBytesTuple: [0x42, 0x00], expectedStr: "AMY" },
  { name: "TOKEN_UNIT_FLT", tokenObj: FLT, expectedBytesTuple: [0x42, 0x01], expectedStr: "FLT" },

  // Orders
  { name: "TOKEN_ORDER_CTO", tokenObj: CTO, expectedBytesTuple: [0x43, 0x20], expectedStr: "CTO" },
  { name: "TOKEN_ORDER_CVY", tokenObj: CVY, expectedBytesTuple: [0x43, 0x21], expectedStr: "CVY" },
  { name: "TOKEN_ORDER_HLD", tokenObj: HLD, expectedBytesTuple: [0x43, 0x22], expectedStr: "HLD" },
  { name: "TOKEN_ORDER_MTO", tokenObj: MTO, expectedBytesTuple: [0x43, 0x23], expectedStr: "MTO" },
  { name: "TOKEN_ORDER_SUP", tokenObj: SUP, expectedBytesTuple: [0x43, 0x24], expectedStr: "SUP" },
  { name: "TOKEN_ORDER_VIA", tokenObj: VIA, expectedBytesTuple: [0x43, 0x25], expectedStr: "VIA" },
  { name: "TOKEN_ORDER_DSB", tokenObj: DSB, expectedBytesTuple: [0x43, 0x40], expectedStr: "DSB" },
  { name: "TOKEN_ORDER_RTO", tokenObj: RTO, expectedBytesTuple: [0x43, 0x41], expectedStr: "RTO" },
  { name: "TOKEN_ORDER_BLD", tokenObj: BLD, expectedBytesTuple: [0x43, 0x80], expectedStr: "BLD" },
  { name: "TOKEN_ORDER_REM", tokenObj: REM, expectedBytesTuple: [0x43, 0x81], expectedStr: "REM" },
  { name: "TOKEN_ORDER_WVE", tokenObj: WVE, expectedBytesTuple: [0x43, 0x82], expectedStr: "WVE" },

  // Order Notes (Results)
  { name: "TOKEN_RESULT_SUC", tokenObj: SUC, expectedBytesTuple: [0x45, 0x00], expectedStr: "SUC" },
  { name: "TOKEN_RESULT_BNC", tokenObj: BNC, expectedBytesTuple: [0x45, 0x01], expectedStr: "BNC" },
  { name: "TOKEN_RESULT_CUT", tokenObj: CUT, expectedBytesTuple: [0x45, 0x02], expectedStr: "CUT" },
  { name: "TOKEN_RESULT_DSR", tokenObj: DSR, expectedBytesTuple: [0x45, 0x03], expectedStr: "DSR" },
  { name: "TOKEN_RESULT_FLD", tokenObj: RESULT_FLD, expectedBytesTuple: [0x45, 0x04], expectedStr: "FLD" },
  { name: "TOKEN_RESULT_NSO", tokenObj: NSO, expectedBytesTuple: [0x45, 0x05], expectedStr: "NSO" },
  { name: "TOKEN_RESULT_RET", tokenObj: RESULT_RET, expectedBytesTuple: [0x45, 0x06], expectedStr: "RET" },

  // Order Notes (THX)
  { name: "TOKEN_ORDER_NOTE_MBV", tokenObj: MBV, expectedBytesTuple: [0x44, 0x00], expectedStr: "MBV" },
  // ... many more THX notes ...
  { name: "TOKEN_ORDER_NOTE_YSC", tokenObj: YSC, expectedBytesTuple: [0x44, 0x13], expectedStr: "YSC" },

  // Coasts
  { name: "TOKEN_COAST_NCS", tokenObj: NCS, expectedBytesTuple: [0x46, 0x00], expectedStr: "NCS" },
  // ... other coasts ...
  { name: "TOKEN_COAST_NWC", tokenObj: NWC, expectedBytesTuple: [0x46, 0x0E], expectedStr: "NWC" },

  // Seasons
  { name: "TOKEN_SEASON_SPR", tokenObj: SPR, expectedBytesTuple: [0x47, 0x00], expectedStr: "SPR" },
  // ... other seasons ...
  { name: "TOKEN_SEASON_WIN", tokenObj: WIN, expectedBytesTuple: [0x47, 0x04], expectedStr: "WIN" },

  // Commands
  { name: "TOKEN_COMMAND_CCD", tokenObj: CCD, expectedBytesTuple: [0x48, 0x00], expectedStr: "CCD" },
  // ... other commands ...
  { name: "TOKEN_COMMAND_SMR", tokenObj: SMR, expectedBytesTuple: [0x48, 0x1E], expectedStr: "SMR" },

  // Parameters
  { name: "TOKEN_PARAMETER_AOA", tokenObj: AOA, expectedBytesTuple: [0x49, 0x00], expectedStr: "AOA" },
  // ... other parameters ...
  { name: "TOKEN_PARAMETER_DSD", tokenObj: DSD, expectedBytesTuple: [0x49, 0x0D], expectedStr: "DSD" },

  // Press
  { name: "TOKEN_PRESS_ALY", tokenObj: ALY, expectedBytesTuple: [0x4A, 0x00], expectedStr: "ALY" },
  // ... other press tokens ...
  { name: "TOKEN_PRESS_UNT", tokenObj: UNT, expectedBytesTuple: [0x4A, 0x24], expectedStr: "UNT" },
  { name: "TOKEN_PRESS_NAR", tokenObj: NAR, expectedBytesTuple: [0x4A, 0x25], expectedStr: "NAR" },
  { name: "TOKEN_PRESS_CCL", tokenObj: CCL, expectedBytesTuple: [0x4A, 0x26], expectedStr: "CCL" },


  // Provinces (selection)
  { name: "TOKEN_PROVINCE_ADR", tokenObj: ADR, expectedBytesTuple: [0x52, 0x0E], expectedStr: "ADR" },
  { name: "TOKEN_PROVINCE_ANK", tokenObj: ANK, expectedBytesTuple: [0x55, 0x30], expectedStr: "ANK" },
  { name: "TOKEN_PROVINCE_STP", tokenObj: STP, expectedBytesTuple: [0x57, 0x4A], expectedStr: "STP" },

  // Symbols
  { name: "TOKEN_SYMBOL_OPE_PAR", tokenObj: OPE_PAR, expectedBytesTuple: [0x40, 0x00], expectedStr: "(" },
  { name: "TOKEN_SYMBOL_CLO_PAR", tokenObj: CLO_PAR, expectedBytesTuple: [0x40, 0x01], expectedStr: ")" },
];


describe('DAIDE Token Definitions and Class Functionality', () => {
  test('all registered tokens should have correct string and byte representations', () => {
    for (const { name, tokenObj, expectedBytesTuple, expectedStr } of expectedTokenData) {
      // Test the pre-registered token instance
      expect(tokenObj.toString()).toBe(expectedStr);
      expect(tokenObj.toBytes()).toEqual(new Uint8Array(expectedBytesTuple));

      // Test creating token from its expected string
      const tokenFromStr = new Token({ from_str: expectedStr });
      expect(tokenFromStr.toBytes()).toEqual(new Uint8Array(expectedBytesTuple));
      expect(tokenFromStr.toString()).toBe(expectedStr);

      // Test creating token from its expected bytes
      const tokenFromBytes = new Token({ from_bytes: new Uint8Array(expectedBytesTuple) });
      expect(tokenFromBytes.toString()).toBe(expectedStr);
      expect(tokenFromBytes.toBytes()).toEqual(new Uint8Array(expectedBytesTuple));

      // Test equality
      expect(tokenObj.equals(tokenFromStr)).toBe(true);
      expect(tokenObj.equals(tokenFromBytes)).toBe(true);
      expect(tokenFromStr.equals(tokenFromBytes)).toBe(true);
    }
  });

  test('Token class should handle integer representations correctly', () => {
    const intToken = new Token({ from_int: 1901 });
    expect(intToken.toInt()).toBe(1901);
    expect(intToken.toString()).toBe("1901");
    // Expected bytes for 1901: 00000111 01101101  (0x07, 0x6D)
    // 14-bit encoding: 00 prefix + 0 sign + 0011101101101
    // 00000111 01101101 --> 0x07, 0x6D
    expect(intToken.toBytes()).toEqual(new Uint8Array([0x07, 0x6D]));

    const tokenFromIntBytes = new Token({ from_bytes: new Uint8Array([0x07, 0x6D]) });
    expect(tokenFromIntBytes.toInt()).toBe(1901);
    expect(tokenFromIntBytes.toString()).toBe("1901");

    const negIntToken = new Token({ from_int: -10 });
      // -10 + 8192 = 8182
      // 8182 in 13-bit binary: 1111111110110
      // Full 16-bit DAIDE (00 + sign_1 + value): 001 1111111110110
      // Byte1: 00111111 (0x3F)
      // Byte2: 11110110 (0xF6)
    expect(negIntToken.toInt()).toBe(-10);
    expect(negIntToken.toString()).toBe("-10");
    expect(negIntToken.toBytes()).toEqual(new Uint8Array([0x3F, 0xF6]));

    const tokenFromNegIntBytes = new Token({ from_bytes: new Uint8Array([0x3F, 0xF6])});
    expect(tokenFromNegIntBytes.toInt()).toBe(-10);
  });

  test('Token class should handle ASCII character representations correctly', () => {
    const asciiToken = new Token({ from_str: 'X' });
    expect(asciiToken.toString()).toBe('X');
    expect(asciiToken.toBytes()).toEqual(new Uint8Array([0x4B, 'X'.charCodeAt(0)])); // 0x4B is ASCII_BYTE_VAL

    const tokenFromAsciiBytes = new Token({ from_bytes: new Uint8Array([0x4B, 'Y'.charCodeAt(0)]) });
    expect(tokenFromAsciiBytes.toString()).toBe('Y');
  });

  test('Token equality should distinguish different tokens', () => {
    expect(AUS.equals(ENG)).toBe(false);
    expect(new Token({from_int: 10}).equals(new Token({from_int: 11}))).toBe(false);
    expect(new Token({from_str: 'A'}).equals(new Token({from_str: 'B'}))).toBe(false);
  });

  test('Invalid token initializations should throw errors or be handled', () => {
    expect(() => new Token({from_str: "VERY_LONG_TOKEN_STR"})).toThrow();
    // Bytes of wrong length
    expect(() => new Token({from_bytes: new Uint8Array([0x01])})).toThrow();
    expect(() => new Token({from_bytes: new Uint8Array([0x01, 0x02, 0x03])})).toThrow();
    // Integer out of range
    expect(() => new Token({from_int: 9000})).toThrow();
    expect(() => new Token({from_int: -9000})).toThrow();
  });
});
