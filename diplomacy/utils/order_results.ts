// diplomacy/utils/order_results.ts
// Contains the results labels and code used by the engine

import { StringableCode } from './common';

// Constants
const ORDER_RESULT_OFFSET = 10000;

export class OrderResult extends StringableCode {
    /**
     * Represents an order result
     * @param code - int code of the order result
     * @param message - human readable string message associated to the order result
     */
    constructor(code: number | null, message: string) { // Allow code to be null as in StringableCode
        super(code, message);
    }
}

export const OK = new OrderResult(0, '');
/**Order result OK, printed as ``''``*/

export const NO_CONVOY = new OrderResult(ORDER_RESULT_OFFSET + 1, 'no convoy');
/**Order result NO_CONVOY, printed as ``'no convoy'``*/

export const BOUNCE = new OrderResult(ORDER_RESULT_OFFSET + 2, 'bounce');
/**Order result BOUNCE, printed as ``'bounce'``*/

export const VOID = new OrderResult(ORDER_RESULT_OFFSET + 3, 'void');
/**Order result VOID, printed as ``'void'``*/

export const CUT = new OrderResult(ORDER_RESULT_OFFSET + 4, 'cut');
/**Order result CUT, printed as ``'cut'``*/

export const DISLODGED = new OrderResult(ORDER_RESULT_OFFSET + 5, 'dislodged');
/**Order result DISLODGED, printed as ``'dislodged'``*/

export const DISRUPTED = new OrderResult(ORDER_RESULT_OFFSET + 6, 'disrupted');
/**Order result DISRUPTED, printed as ``'disrupted'``*/

export const DISBAND = new OrderResult(ORDER_RESULT_OFFSET + 7, 'disband');
/**Order result DISBAND, printed as ``'disband'``*/

export const MAYBE = new OrderResult(ORDER_RESULT_OFFSET + 8, 'maybe');
/**Order result MAYBE, printed as ``'maybe'``*/

// Note: The enum OrderResult in diplomacy/engine/interfaces.ts
// currently defines these as string enum values (e.g., OrderResult.NO_CONVOY = 'no convoy').
// This new OrderResult class provides richer objects with codes and messages.
// These two representations will need to be reconciled in a future step.
// For instance, game logic might use these class instances, but expose
// only `OrderResult.message` to align with the string enum values if needed elsewhere.
// Or, the string enum in interfaces.ts might be replaced by using these constants' messages.
// Example: `import { NO_CONVOY } from '../utils/order_results'; console.log(NO_CONVOY.message)` -> 'no convoy'
