// diplomacy/utils/parsing.ts

import { DiplomacyException, TypeException, ValueException, CommonKeyException } from './exceptions';
import { is_dictionary, is_sequence } from './common';
import { Jsonable } from './jsonable'; // Import for JsonableClassType; may cause circular dependency if not handled carefully at runtime

const logger = {
    error: (message: string, ...args: any[]) => console.error('[Parsing]', message, ...args),
    warn: (message: string, ...args: any[]) => console.warn('[Parsing]', message, ...args),
};

// --- Base ParserType Class ---
export abstract class ParserType {
    // JS primitives: string, number, boolean, object (for dicts), null, undefined.
    // Python also had bytes. We'll map Python's int/float to number.
    // `object` is a loose term here; more specific checks happen in subclasses.
    protected static primitives = [String, Number, Boolean, Object, Array, Set, Map, Date];

    abstract validate(element: any): void;

    update(element: any): any {
        return element;
    }

    to_type(json_value: any): any {
        return json_value;
    }

    to_json(raw_value: any): any {
        if (raw_value instanceof Date) return raw_value.toISOString();
        if (raw_value instanceof Set) return Array.from(raw_value);
        if (raw_value instanceof Map) return Object.fromEntries(raw_value);
        if (raw_value && typeof (raw_value as any).toDict === 'function') {
            return (raw_value as any).toDict(); // For Jsonable instances
        }
        if (raw_value && typeof (raw_value as any).toJSON === 'function') {
            return (raw_value as any).toJSON(); // For classes with toJSON (like Date, but handled above)
        }
        return raw_value;
    }
}

// --- Concrete ParserType Subclasses ---

export class PrimitiveType extends ParserType {
    constructor(public element_type: Function) { // e.g., String, Number, Boolean, Object (for dict)
        super();
        if (![String, Number, Boolean, Object].includes(element_type)) {
            throw new DiplomacyException(`Expected a JS primitive constructor (String, Number, Boolean, Object), got ${element_type}`);
        }
    }

    toString(): string {
        return this.element_type.name;
    }

    validate(element: any): void {
        if (this.element_type === String && typeof element !== 'string') {
            throw new TypeException(this.element_type.name, typeof element);
        } else if (this.element_type === Number && typeof element !== 'number') {
            throw new TypeException(this.element_type.name, typeof element);
        } else if (this.element_type === Boolean && typeof element !== 'boolean') {
            throw new TypeException(this.element_type.name, typeof element);
        } else if (this.element_type === Object && (typeof element !== 'object' || element === null || Array.isArray(element))) {
            // Basic check for "dictionary-like" plain objects
            throw new TypeException('object (plain)', Array.isArray(element) ? 'array' : typeof element);
        }
    }
}

export class DefaultValueType extends ParserType {
    public element_type_parser: ParserType;

    constructor(element_type: any, public default_json_value: any) {
        super();
        this.element_type_parser = get_type(element_type);
        if (this.element_type_parser instanceof DefaultValueType || this.element_type_parser instanceof OptionalValueType) {
            throw new DiplomacyException("DefaultValueType cannot wrap another DefaultValueType or OptionalValueType.");
        }
        // Validate the default value itself at construction time
        if (default_json_value !== null && default_json_value !== undefined) {
             const typed_default = this.element_type_parser.to_type(default_json_value);
             this.element_type_parser.validate(typed_default);
        }
    }

    toString(): string {
        return `${this.element_type_parser.toString()} (default ${JSON.stringify(this.default_json_value)})`;
    }

    validate(element: any): void {
        if (element !== null && element !== undefined) {
            this.element_type_parser.validate(element);
        }
    }

    update(element: any): any {
        if (element !== null && element !== undefined) {
            return this.element_type_parser.update(element);
        }
        return (this.default_json_value === null || this.default_json_value === undefined)
               ? this.default_json_value
               : this.element_type_parser.to_type(this.default_json_value);
    }

    to_type(json_value: any): any {
        const value_to_convert = (json_value === null || json_value === undefined) ? this.default_json_value : json_value;
        if (value_to_convert === null || value_to_convert === undefined) return value_to_convert;
        return this.element_type_parser.to_type(value_to_convert);
    }

    to_json(raw_value: any): any {
        if (raw_value === null || raw_value === undefined) {
            // If default_json_value is also null/undefined, return that.
            // Otherwise, this implies the raw_value represents the default, so serialize default.
            // This logic can be tricky. Python's copy(self.default_json_value) is safer.
            return this.default_json_value === null || this.default_json_value === undefined ? this.default_json_value : JSON.parse(JSON.stringify(this.default_json_value));
        }
        return this.element_type_parser.to_json(raw_value);
    }
}

export class OptionalValueType extends DefaultValueType {
    constructor(element_type: any) {
        super(element_type, null); // Default is null for optional values
    }
     toString(): string {
        return `${this.element_type_parser.toString()} | null`;
    }
}

export class SequenceType extends ParserType {
    public element_type_parser: ParserType;

    constructor(element_type: any, public sequence_builder: ((seq: any[]) => any) | null = null) {
        super();
        this.element_type_parser = get_type(element_type);
        this.sequence_builder = sequence_builder || ((seq) => seq);
    }

    toString(): string {
        return `Array<${this.element_type_parser.toString()}>`;
    }

    validate(element: any): void {
        if (!is_sequence(element)) { // is_sequence from common.ts should check for Array.isArray
            throw new TypeException('sequence (Array)', typeof element);
        }
        for (const seq_element of element) {
            this.element_type_parser.validate(seq_element);
        }
    }

    update(element: any): any {
        const sequence = (element as any[]).map(seq_element => this.element_type_parser.update(seq_element));
        return this.sequence_builder!(sequence);
    }

    to_type(json_value: any[]): any {
        if (!Array.isArray(json_value)) throw new TypeException('array', typeof json_value);
        const sequence = json_value.map(seq_element => this.element_type_parser.to_type(seq_element));
        return this.sequence_builder!(sequence);
    }

    to_json(raw_value: any[]): any[] {
        if (!Array.isArray(raw_value)) throw new TypeException('array', typeof raw_value);
        return raw_value.map(seq_element => this.element_type_parser.to_json(seq_element));
    }
}

export class JsonableClassType extends ParserType {
    constructor(public element_type: typeof Jsonable) { // Expects a constructor of a Jsonable subclass
        super();
        if (!(typeof element_type === 'function' && element_type.prototype instanceof Jsonable)) {
             throw new DiplomacyException(`Expected a class extending Jsonable, got ${element_type}`);
        }
    }

    toString(): string {
        return this.element_type.name;
    }

    validate(element: any): void {
        if (!(element instanceof this.element_type)) {
            throw new TypeException(this.element_type.name, element?.constructor?.name || typeof element);
        }
    }

    to_type(json_value: Record<string, any>): Jsonable {
        if (typeof json_value !== 'object' || json_value === null) {
            throw new TypeException('object (for Jsonable)', typeof json_value);
        }
        return (this.element_type as any).fromDict(json_value);
    }

    to_json(raw_value: Jsonable): Record<string, any> {
        if (!(raw_value instanceof this.element_type)) {
             throw new TypeException(this.element_type.name, raw_value?.constructor?.name || typeof raw_value);
        }
        return raw_value.toDict();
    }
}


// --- Helper Functions ---

export function get_type(desired_type: any): ParserType {
    if (desired_type instanceof ParserType) {
        return desired_type;
    }
    if (desired_type === String || desired_type === Number || desired_type === Boolean || desired_type === Object) {
        return new PrimitiveType(desired_type);
    }
    // Basic check for Jsonable subclasses (constructor)
    if (typeof desired_type === 'function' && desired_type.prototype instanceof Jsonable) {
        return new JsonableClassType(desired_type as typeof Jsonable);
    }
    // Add more sophisticated checks if needed, e.g., for Array to map to SequenceType
    // This part would need to be more robust to match Python's dynamic get_type fully.
    // For now, assuming explicit ParserType instances (e.g., new SequenceType(String)) are used in models.

    // Fallback for unhandled types - this indicates an issue with model definition or get_type itself
    logger.warn(`get_type: Unhandled desired_type: ${desired_type}. Defaulting to PrimitiveType(Object) if it's a constructor, else error.`);
    if (typeof desired_type === 'function') return new PrimitiveType(Object); // A guess for unknown classes
    throw new DiplomacyException(`Cannot determine ParserType for: ${desired_type}`);
}


export function to_type(json_value: any, parser_type_input: any): any {
    return get_type(parser_type_input).to_type(json_value);
}

export function to_json(raw_value: any, parser_type_input: any): any {
    return get_type(parser_type_input).to_json(raw_value);
}

export function validate_data(data: Record<string, any>, model: Record<string, any>): void {
    if (!is_dictionary(data)) throw new TypeException("object", typeof data);
    if (!is_dictionary(model)) throw new TypeException("object", typeof model);

    for (const model_key in model) {
        if (model.hasOwnProperty(model_key)) {
            const model_type_descriptor = model[model_key];
            try {
                get_type(model_type_descriptor).validate(data[model_key]);
            } catch (exception: any) {
                logger.error(`Error occurred while checking key ${model_key}`);
                throw exception;
            }
        }
    }
}

export function update_data(data: Record<string, any>, model: Record<string, any>): Record<string, any> {
    const updatedData = { ...data };
    for (const model_key in model) {
        if (model.hasOwnProperty(model_key)) {
            const model_type_descriptor = model[model_key];
            const data_value = data.hasOwnProperty(model_key) ? data[model_key] : undefined; // Use undefined if key missing for DefaultValueType
            updatedData[model_key] = get_type(model_type_descriptor).update(data_value);
        }
    }
    return updatedData;
}

// --- Remaining ParserType Subclasses ---

export class ConverterType extends ParserType {
    public element_type_parser: ParserType;

    constructor(
        element_type: any,
        public converter_function: (value: any) => any,
        public json_converter_function?: (json_value: any) => any
    ) {
        super();
        this.element_type_parser = get_type(element_type);
        if (this.element_type_parser instanceof ConverterType) {
            throw new DiplomacyException("ConverterType cannot wrap another ConverterType.");
        }
        if (typeof converter_function !== 'function') {
            throw new DiplomacyException("converter_function must be a function.");
        }
        this.json_converter_function = json_converter_function || converter_function;
    }

    validate(element: any): void {
        this.element_type_parser.validate(this.converter_function(element));
    }

    update(element: any): any {
        return this.element_type_parser.update(this.converter_function(element));
    }

    to_type(json_value: any): any {
        return this.element_type_parser.to_type(this.json_converter_function!(json_value));
    }

    to_json(raw_value: any): any {
        // Raw value is already of the target type after conversion by the main class using this.
        // So, we directly pass it to the wrapped parser's to_json.
        // The converter_function is used when setting/updating the attribute on the object.
        return this.element_type_parser.to_json(raw_value);
    }
}

export class StringableType extends ParserType {
    private use_from_string: boolean;

    constructor(public element_type: { new(...args: any[]): any; from_string?: (s: string) => any; name: string }) {
        super();
        this.use_from_string = typeof this.element_type.from_string === 'function';
    }

    toString(): string {
        return this.element_type.name;
    }

    validate(element: any): void {
        if (!(element instanceof this.element_type)) {
            try {
                const element_to_str = this.to_json(element); // Converts to string via element.toString()
                const element_from_str = this.to_type(element_to_str); // Converts back via new() or from_string()
                const element_from_str_to_str = this.to_json(element_from_str);
                if (element_to_str !== element_from_str_to_str) {
                    throw new TypeException(this.element_type.name, typeof element, "Value not consistently stringable/parsable.");
                }
            } catch (e) {
                throw new TypeException(this.element_type.name, typeof element, `Validation failed: ${e}`);
            }
        }
    }

    to_type(json_value: string): any {
        if (typeof json_value !== 'string') throw new TypeException('string', typeof json_value);
        if (this.use_from_string) {
            return this.element_type.from_string!(json_value);
        }
        return new this.element_type(json_value);
    }

    to_json(raw_value: any): string {
        if (!(raw_value instanceof this.element_type) && typeof raw_value?.toString !== 'function') {
            throw new TypeException(this.element_type.name, typeof raw_value);
        }
        return String(raw_value);
    }
}

export class DictType extends ParserType {
    public key_type_parser: StringableType; // Keys must be stringable
    public val_type_parser: ParserType;

    constructor(
        key_type: any, // Should be a constructor for a stringable type (String, Number, or class for StringableType)
        val_type: any,
        public dict_builder: ((dict: Record<string, any> | Map<any,any>) => any) | null = null
    ) {
        super();
        this.key_type_parser = (key_type instanceof StringableType) ? key_type : new StringableType(key_type);
        this.val_type_parser = get_type(val_type);
        this.dict_builder = dict_builder || ((dict) => dict);
    }

    toString(): string {
        return `Record<${this.key_type_parser.toString()}, ${this.val_type_parser.toString()}>`;
    }

    validate(element: any): void {
        if (!is_dictionary(element) && !(element instanceof Map)) {
            throw new TypeException('dictionary or Map', typeof element);
        }
        const entries = (element instanceof Map) ? element.entries() : Object.entries(element);
        for (const [key, value] of entries) {
            this.key_type_parser.validate(key); // Key should be validated against its original type before to_json for Map keys
            this.val_type_parser.validate(value);
        }
    }

    update(element: any): any {
        const result_dict: Record<string, any> = {};
        const entries = (element instanceof Map) ? element.entries() : Object.entries(element);
        for (const [key, value] of entries) {
            result_dict[this.key_type_parser.update(key)] = this.val_type_parser.update(value);
        }
        return this.dict_builder!(result_dict);
    }

    to_type(json_value: Record<string, any>): any {
        if (!is_dictionary(json_value)) throw new TypeException('object (dictionary)', typeof json_value);
        const result_dict: Record<string, any> = {};
        for (const key in json_value) {
            if (json_value.hasOwnProperty(key)) {
                result_dict[this.key_type_parser.to_type(key)] = this.val_type_parser.to_type(json_value[key]);
            }
        }
        return this.dict_builder!(result_dict);
    }

    to_json(raw_value: Record<string, any> | Map<any,any>): Record<string, any> {
         if (!is_dictionary(raw_value) && !(raw_value instanceof Map)) {
            throw new TypeException('dictionary or Map', typeof raw_value);
        }
        const result_json_dict: Record<string, any> = {};
        const entries = (raw_value instanceof Map) ? raw_value.entries() : Object.entries(raw_value);
        for (const [key, value] of entries) {
            result_json_dict[this.key_type_parser.to_json(key)] = this.val_type_parser.to_json(value);
        }
        return result_json_dict;
    }
}

export class IndexedSequenceType extends ParserType {
    public dict_type_parser: DictType;
    public sequence_type_parser: SequenceType;

    constructor(dict_type: DictType, public key_name: string) {
        super();
        if (!(dict_type instanceof DictType)) {
            throw new DiplomacyException("IndexedSequenceType requires a DictType instance.");
        }
        this.dict_type_parser = dict_type;
        // The elements of the sequence are the values of the dictionary
        this.sequence_type_parser = new SequenceType(this.dict_type_parser.val_type_parser);
    }

    toString(): string {
        return `IndexedSequence<${this.dict_type_parser.val_type_parser.toString()}, key: ${this.key_name}>`;
    }

    validate(element: any): void { // Element in memory is a Map/object (dictionary)
        this.dict_type_parser.validate(element);
    }

    update(element: any): any { // Element in memory is a Map/object
        return this.dict_type_parser.update(element);
    }

    to_json(raw_value: Record<string, any> | Map<any, any>): any[] { // raw_value is a Map or object
        const values = (raw_value instanceof Map) ? Array.from(raw_value.values()) : Object.values(raw_value);
        return this.sequence_type_parser.to_json(values);
    }

    to_type(json_value: any[]): any { // json_value is an array from JSON
        if (!Array.isArray(json_value)) throw new TypeException('array', typeof json_value);
        const loaded_sequence = this.sequence_type_parser.to_type(json_value);
        const result_dict: Record<string, any> = {};
        for (const element of loaded_sequence) {
            if (element && typeof element === 'object' && this.key_name in element) {
                const key = (element as any)[this.key_name];
                result_dict[this.key_type_parser.to_type(String(key))] = element; // Element is already to_type'd by sequence_type_parser
            } else {
                logger.warn(`IndexedSequenceType: Element missing key_name '${this.key_name}' or not an object.`, element);
            }
        }
        return this.dict_type_parser.dict_builder!(result_dict); // Apply dict_builder if any
    }
}

export class EnumerationType extends ParserType {
    public enum_values: Set<any>;

    constructor(enum_values: any[]) {
        super();
        if (!Array.isArray(enum_values) || enum_values.length === 0) {
            throw new DiplomacyException("EnumerationType requires a non-empty array of values.");
        }
        // Ensure all enum_values are primitives for reliable comparison
        enum_values.forEach(val => {
            if (typeof val !== 'string' && typeof val !== 'number' && typeof val !== 'boolean') {
                throw new DiplomacyException("EnumerationType values must be primitives (string, number, boolean).");
            }
        });
        this.enum_values = new Set(enum_values);
    }

    toString(): string {
        return `Enum<${Array.from(this.enum_values).map(String).join(" | ")}>`;
    }

    validate(element: any): void {
        if (!this.enum_values.has(element)) {
            throw new ValueException(Array.from(this.enum_values), element);
        }
    }
    // to_type and to_json are default from ParserType (identity)
}

export class SequenceOfPrimitivesType extends ParserType {
    public allowed_primitive_constructors: Function[]; // e.g. [String, Number]

    constructor(seq_of_primitives: Function[]) {
        super();
        if (!Array.isArray(seq_of_primitives) || seq_of_primitives.length === 0) {
            throw new DiplomacyException("SequenceOfPrimitivesType requires a non-empty array of primitive constructors.");
        }
        seq_of_primitives.forEach(p => {
            if (![String, Number, Boolean, Object].includes(p)) {
                 throw new DiplomacyException(`Invalid primitive constructor in SequenceOfPrimitivesType: ${p}`);
            }
        });
        this.allowed_primitive_constructors = seq_of_primitives;
    }

    toString(): string {
        return `Primitives<${this.allowed_primitive_constructors.map(p => p.name).join(" | ")}>`;
    }

    validate(element: any): void {
        const typeOfElement = typeof element;
        const constructorOfElement = element?.constructor;

        const isValid = this.allowed_primitive_constructors.some(primitiveConstructor => {
            if (primitiveConstructor === String && typeOfElement === 'string') return true;
            if (primitiveConstructor === Number && typeOfElement === 'number') return true;
            if (primitiveConstructor === Boolean && typeOfElement === 'boolean') return true;
            if (primitiveConstructor === Object && typeOfElement === 'object' && element !== null && !Array.isArray(element)) return true;
            return false;
        });

        if (!isValid) {
            throw new TypeException(this.allowed_primitive_constructors.map(p => p.name).join(' or '), constructorOfElement?.name || typeOfElement);
        }
    }
     // to_type and to_json are default from ParserType (identity)
}


// --- Helper Functions (update_model, extend_model) ---
export function update_model(model: Record<string, any>, additional_keys: Record<string, any>, allow_duplicate_keys: boolean = true): Record<string, any> {
    if (!is_dictionary(model)) throw new TypeException("object", typeof model);
    if (!is_dictionary(additional_keys)) throw new TypeException("object", typeof additional_keys);

    if (!allow_duplicate_keys) {
        assert_no_common_keys(model, additional_keys);
    }
    return { ...model, ...additional_keys };
}

export function extend_model(model: Record<string, any>, additional_keys: Record<string, any>): Record<string, any> {
    return update_model(model, additional_keys, false);
}
