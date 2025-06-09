// diplomacy/utils/common.ts
// Common utils symbols used in diplomacy network code.

import * as crypto from 'crypto';
import { Buffer } from 'buffer'; // Needed for Base64 operations

// Placeholder for exceptions - will be imported from a dedicated exceptions file later
class CommonKeyException extends Error {
    constructor(key: string) {
        super(`Common key found: ${key}`);
        this.name = 'CommonKeyException';
    }
}

// Datetime since timestamp 0.
export const EPOCH = new Date(Date.UTC(1970, 0, 1, 0, 0, 0));

// Regex used for conversion from camel case to snake case.
const REGEX_CONSECUTIVE_UPPER_CASES = /[A-Z]{2,}/g; // Adjusted for JS: removed compile, added g
const REGEX_LOWER_THEN_UPPER_CASES = /([a-z0-9])([A-Z])/g; // Adjusted for JS: removed compile, added g
const REGEX_UNDERSCORE_THEN_LETTER = /_([a-z])/g; // Adjusted for JS: removed compile, added g
const REGEX_START_BY_LOWERCASE = /^[a-z]/; // Adjusted for JS: removed compile

/**
 * Hash long password to allow bcrypt to handle password longer than 72 characters.
 * Module private method.
 * @param password - password to hash.
 * @returns The hashed password, base64 encoded.
 */
function _sub_hash_password(password: string): string {
    // Bcrypt only handles passwords up to 72 characters. We use this hashing method as a work around.
    // Suggested in bcrypt PyPI page (2018/02/08 12:36 EST): https://pypi.python.org/pypi/bcrypt/3.1.0
    const hash = crypto.createHash('sha256');
    hash.update(password, 'utf-8');
    return hash.digest('base64');
}

/**
 * Check if password matches hashed.
 * NOTE: This is a STUB and NOT a secure bcrypt replacement.
 * @param password - password to check.
 * @param hashed - a password hashed with hash_password().
 * @returns Indicates if the password matches the hash.
 */
export function is_valid_password(password: string, hashed: string): boolean {
    console.warn("`is_valid_password` is using a STUB comparison and is NOT SECURE.");
    // In a real scenario, use a library like bcrypt.compareSync()
    // This stub assumes `hashed` is the output of our stubbed `hash_password`.
    const sub_hashed_password = _sub_hash_password(password);
    // Example: if hash_password just appended a salt, check that.
    // This is highly insecure and just for structure.
    return hashed.startsWith(sub_hashed_password);
}

/**
 * Hash password. Accepts password longer than 72 characters. Public method.
 * NOTE: This is a STUB and NOT a secure bcrypt replacement.
 * @param password - The password to hash
 * @returns The hashed password.
 */
export function hash_password(password: string): string {
    console.warn("`hash_password` is a STUB and is NOT SECURE. It does not use bcrypt salts.");
    // In a real scenario, use a library like bcrypt.hashSync()
    const sub_hashed = _sub_hash_password(password);
    // This is just a placeholder, not a real salt process.
    return `${sub_hashed}$INSECURE_STUB_SALT`;
}

/**
 * Generate a token with 2 * n_bytes characters (n_bytes bytes encoded in hexadecimal).
 */
export function generate_token(n_bytes: number = 128): string {
    return crypto.randomBytes(n_bytes).toString('hex');
}

/**
 * Check if given variable is a dictionary-like object (plain object in JS/TS).
 * @param dict_to_check - Object to check.
 * @returns Indicates if the object is a plain object.
 */
export function is_dictionary(dict_to_check: any): boolean {
    return typeof dict_to_check === 'object' && dict_to_check !== null && !Array.isArray(dict_to_check) && !(dict_to_check instanceof Date);
}

/**
 * Check if given variable is a sequence-like object (array in JS/TS).
 * Note that strings will not be considered as sequences.
 * @param seq_to_check - Sequence-like object to check.
 * @returns Indicates if the object is array-like.
 */
export function is_sequence(seq_to_check: any): boolean {
    // Strings and dicts are not valid sequences.
    if (typeof seq_to_check === 'string' || is_dictionary(seq_to_check)) {
        return false;
    }
    return Array.isArray(seq_to_check) || (typeof seq_to_check === 'object' && seq_to_check !== null && typeof (seq_to_check as any)[Symbol.iterator] === 'function');
}

/**
 * Convert a string (expected to be in camel case) to snake case.
 * @param name - string to convert.
 * @returns snake case version of given name.
 */
export function camel_case_to_snake_case(name: string): string {
    if (name === '') {
        return name;
    }
    // Python: separated_consecutive_uppers = REGEX_CONSECUTIVE_UPPER_CASES.sub(lambda m: '_'.join(c for c in m.group(0)), name)
    // JS:
    let separated_consecutive_uppers = name.replace(REGEX_CONSECUTIVE_UPPER_CASES, (match) => {
        return Array.from(match).join('_');
    });
    // Python: return REGEX_LOWER_THEN_UPPER_CASES.sub(r'\1_\2', separated_consecutive_uppers).lower()
    // JS:
    return separated_consecutive_uppers.replace(REGEX_LOWER_THEN_UPPER_CASES, '$1_$2').toLowerCase();
}

/**
 * Convert a string (expected to be in snake case) to camel case and convert first letter
 * to upper case if it's in lowercase.
 * @param name - string to convert.
 * @returns camel case version of given name.
 */
export function snake_case_to_upper_camel_case(name: string): string {
    if (name === '') {
        return name;
    }
    // Python: first_lower_case_to_upper = REGEX_START_BY_LOWERCASE.sub(lambda m: m.group(0).upper(), name)
    // JS:
    let first_lower_case_to_upper = name.replace(REGEX_START_BY_LOWERCASE, (match) => match.toUpperCase());
    // Python: return REGEX_UNDERSCORE_THEN_LETTER.sub(lambda m: m.group(1).upper(), first_lower_case_to_upper)
    // JS:
    return first_lower_case_to_upper.replace(REGEX_UNDERSCORE_THEN_LETTER, (match, charAfterUnderscore) => charAfterUnderscore.toUpperCase());
}

/**
 * Check that dictionaries does not share keys.
 */
export function assert_no_common_keys(dict1: object, dict2: object): void {
    const keys1 = Object.keys(dict1);
    const keys2 = Object.keys(dict2);

    let smallest_dict_keys: string[], biggest_dict: object;
    if (keys1.length < keys2.length) {
        smallest_dict_keys = keys1;
        biggest_dict = dict2;
    } else {
        smallest_dict_keys = keys2;
        biggest_dict = dict1;
    }
    for (const key of smallest_dict_keys) {
        if (key in biggest_dict) {
            throw new CommonKeyException(key);
        }
    }
}

/**
 * Return current timestamp with microsecond resolution.
 * Note: JavaScript's Date.now() is milliseconds. For microseconds, multiply by 1000.
 * For more precise microsecond timing, process.hrtime() could be used in Node.js,
 * but this simple multiplication matches the Python version's intent if not its exact precision source.
 */
export function timestamp_microseconds(): number {
    // Python: delta = datetime.now() - EPOCH
    // return (delta.days * 24 * 60 * 60 + delta.seconds) * 1000000 + delta.microseconds
    return Date.now() * 1000;
}


/**
 * Return a new class to be used as string comparator for sorting.
 */
export function str_cmp_class<T extends string>(compare_function: (a: T, b: T) => number): { new(value: T): { value: T, toString(): string } } {
    class StringComparator {
        public value: T;
        private cmp_fn: (a: T, b: T) => number;

        constructor(value: T) {
            this.value = value; // Already a string in TS context generally
            this.cmp_fn = compare_function;
        }

        toString(): string {
            return this.value;
        }

        // These methods are what Array.prototype.sort() would look for if comparing instances directly.
        // However, usually, you pass a compare function to sort.
        // For compatibility with Python's use (e.g. storing these wrapped objects in a list and calling sort()),
        // one might need a custom sort that extracts .value or uses these.
        // For direct use in JS sort: list.sort((a, b) => a.cmp_fn(a.value, b.value))

        // Not directly used by Array.sort in JS, but good for completeness if objects are compared.
        equals(other: StringComparator | string): boolean {
            const otherValue = (typeof other === 'string') ? other : other.value;
            return this.cmp_fn(this.value, otherValue as T) === 0;
        }

        lessThan(other: StringComparator | string): boolean {
            const otherValue = (typeof other === 'string') ? other : other.value;
            return this.cmp_fn(this.value, otherValue as T) < 0;
        }
    }
    // To make it somewhat unique like Python's id()-based naming, though not strictly necessary in TS.
    // Object.defineProperty(StringComparator, 'name', { value: `StringComparator${Date.now()}${Math.random()}` });
    return StringComparator;
}


/**
 * Convert element to a string and make sure string is wrapped in either simple quotes
 * (if contains double quotes) or double quotes (if contains simple quotes).
 * If no quotes, or both types of quotes, defaults to double quotes.
 */
export function to_string_with_quoting(element: any): string {
    const s_element = String(element);
    const hasDouble = s_element.includes('"');
    const hasSingle = s_element.includes("'");

    if (hasDouble && !hasSingle) {
        return `'${s_element}'`;
    }
    // Default to double quotes if no quotes, or if both types are present (escaping would be needed for correctness in that case)
    return `"${s_element}"`;
}


export class StringableCode {
    public readonly code: number | null;
    public readonly message: string;

    constructor(code: number | string, message?: string) {
        if (typeof code === 'string' && message === undefined) {
            const message_parts = code.split(':');
            if (message_parts.length > 1 && /^\d+$/.test(message_parts[0]!)) {
                this.code = parseInt(message_parts[0]!, 10);
                this.message = message_parts.slice(1).join(':');
            } else {
                this.code = null;
                this.message = code;
            }
        } else if (typeof code === 'number' && message !== undefined) {
            this.code = code;
            this.message = message;
        } else if (typeof code === 'number' && message === undefined) { // Only code provided
            this.code = code;
            this.message = String(code);
        }
         else { // Fallback or error
            this.code = null;
            this.message = String(code); // Treat code as message if types are unexpected
        }
    }

    equals(other: StringableCode | string | number): boolean {
        if (other instanceof StringableCode) {
            return this.code === other.code;
        }
        // In Python, it compared self._message == str(other).
        // For more robustness, we might compare code if other is number, message if string.
        if (typeof other === 'number' && this.code !== null) {
            return this.code === other;
        }
        return this.message === String(other);
    }

    // __hash__ is not directly applicable in JS/TS objects for Map keys in the same way.
    // If used as Map keys, the object reference is used, or toString() for string-keyed maps.

    // Python's __mod__ was for string formatting like 'Error: %s' % value
    format(...values: any[]): StringableCode {
        let formatted_message = this.message;
        for (const value of values) {
            formatted_message = formatted_message.replace(/%s/, String(value)); // Simple %s replacement
        }
        // More sophisticated formatting would require a proper sprintf-js or similar.
        return new StringableCode(this.code, formatted_message);
    }

    toString(): string {
        return this.message;
    }

    get repr(): string { // Getter for representation
        return `${this.code}:${this.message}`;
    }
}

// Stub for Tornado utilities, as Tornado is Python-specific.
export class Tornado {
    /**
     * Modify exception handler method of given IO loop so that IO loop stops and raises
     * as soon as an exception is thrown from a callback.
     * @param io_loop - IO loop (Tornado specific, type any for TS)
     */
    static stop_loop_on_callback_error(io_loop: any): void {
        console.warn("Tornado.stop_loop_on_callback_error is a STUB and not applicable in typical Node.js environments.");
        // In a Node.js/TS environment, unhandled exceptions in async operations
        // would typically be caught by process.on('uncaughtException') or promise .catch() handlers.
    }
}
