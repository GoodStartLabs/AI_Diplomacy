// diplomacy/utils/game_phase_data.ts
/**
 * Utility class to save all data related to one game phase (phase name, state, messages and orders).
 */

import { Jsonable } from './jsonable';
import * as parsing from './parsing';
import { StringableCode } from './common';
// Placeholder for Message class, assuming it will extend Jsonable
// import { Message } from '../engine/message';

// --- Placeholder for Message ---
// This would normally be imported from '../engine/message'
// For now, let's define a minimal placeholder that extends Jsonable
// to allow `JsonableClassType` to work.
class MessagePlaceholder extends Jsonable {
    static model = {
        time_sent: parsing.PrimitiveType(Number), // Assuming 'time_sent' is part of Message model for IndexedSequenceType
        // ... other message fields
    };
    public time_sent: number = 0;
    // Add other properties as needed for Message if they are accessed by GamePhaseData or its model
    constructor(kwargs: any) {
        super(kwargs);
        this.time_sent = kwargs.time_sent || 0;
    }
}
// --- End Placeholder for Message ---


// Placeholder for string constants, replace with actual imports or definitions later
const STRINGS = {
    NAME: 'name',
    STATE: 'state',
    ORDERS: 'orders',
    RESULTS: 'results',
    MESSAGES: 'messages',
    SUMMARY: 'summary', // Added based on python model keys
    STATISTICAL_SUMMARY: 'statistical_summary' // Added
};

// MESSAGES_TYPE from Python:
// parsing.IndexedSequenceType(
//     parsing.DictType(int, parsing.JsonableClassType(Message), SortedDict.builder(int, Message)),
//     'time_sent'
// )
// For SortedDict.builder, we'll use a Map which preserves insertion order.
// If strict sorting by key is needed beyond that, it has to be handled during processing.
const MESSAGES_DICT_TYPE = new parsing.DictType(
    Number, // Keys are timestamps (int in Python)
    new parsing.JsonableClassType(MessagePlaceholder as any), // Values are Message objects
    (mapData: Record<string | number, MessagePlaceholder>) => new Map(Object.entries(mapData).map(([k, v]) => [Number(k), v])) // Builder to ensure Map
);

const MESSAGES_TYPE_PARSER = new parsing.IndexedSequenceType(MESSAGES_DICT_TYPE, 'time_sent');
export { MESSAGES_TYPE_PARSER as MESSAGES_TYPE_PLACEHOLDER }; // For game.ts if it uses this alias

export interface GamePhaseDataData {
    name: string;
    state: Record<string, any>;
    orders: Record<string, string[] | null>;
    results: Record<string, StringableCode[]>;
    messages: MessagePlaceholder[]; // Serialized as an array by IndexedSequenceType
    summary?: string | null;
    statistical_summary?: string | null;
}


export class GamePhaseData extends Jsonable {
    public name: string;
    public state: Record<string, any>; // Generic dictionary for game state
    public orders: Record<string, string[] | null>; // PowerName -> list of order strings or null
    public results: Record<string, StringableCode[]>; // UnitName -> list of StringableCode results
    public messages: Map<number, MessagePlaceholder>; // Timestamp -> Message object (Map from MESSAGES_DICT_TYPE builder)
    public summary: string | null;
    public statistical_summary: string | null;

    static model: Record<string, any> = {
        [STRINGS.NAME]: new parsing.PrimitiveType(String),
        [STRINGS.STATE]: new parsing.PrimitiveType(Object), // Validates as a plain object
        [STRINGS.ORDERS]: new parsing.DictType(String, new parsing.OptionalValueType(new parsing.SequenceType(String))),
        [STRINGS.RESULTS]: new parsing.DictType(String, new parsing.SequenceType(new parsing.StringableType(StringableCode))),
        [STRINGS.MESSAGES]: MESSAGES_TYPE_PARSER,
        [STRINGS.SUMMARY]: new parsing.OptionalValueType(new parsing.PrimitiveType(String)),
        [STRINGS.STATISTICAL_SUMMARY]: new parsing.OptionalValueType(new parsing.PrimitiveType(String)),
    };

    constructor(data: Partial<GamePhaseDataData> = {}) {
        // Initialize properties to default values first
        this.name = '';
        this.state = {};
        this.orders = {};
        this.results = {};
        this.messages = new Map<number, MessagePlaceholder>();
        this.summary = null;
        this.statistical_summary = null;

        // Let Jsonable constructor handle kwargs based on the model
        super(data);

        // Ensure correct types after super call, especially for those with builders or complex initializations
        // The Jsonable constructor with parsing.update_data should handle defaults from the model.
        // For MESSAGES_TYPE_PARSER, the `to_type` within IndexedSequenceType (which calls DictType's to_type)
        // should use the Map builder.
        if (data.messages && !(this.messages instanceof Map) && Array.isArray(data.messages)) {
             // If super didn't correctly make it a Map due to parsing_to_type not being fully recursive with builders yet
            this.messages = MESSAGES_TYPE_PARSER.to_type(data.messages) as Map<number, MessagePlaceholder>;
        }
    }
     // toDict will be inherited from Jsonable, using the static model.
    // fromDict will be inherited from Jsonable, using the static model.
}
