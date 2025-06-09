// diplomacy/utils/sorted_dict.ts
// Helper class to provide a dict with sorted keys.

import { is_dictionary } from './common';
import { SortedSet } from './sorted_set';
import { TypeException } from './exceptions';

// Define a type for the comparison function for SortedSet keys
export type CompareFn<K> = (a: K, b: K) => number;

export class SortedDict<K, V> {
    private _keys: SortedSet<K>;
    private _couples: Map<K, V>;
    private _keyTypeConstructor: (new (...args: any[]) => K) | Function | undefined; // For potential runtime checks
    private _valueTypeConstructor: (new (...args: any[]) => V) | Function;

    /**
     * Initialize a typed SortedDict.
     * @param keyTypeOrCompareFn Expected type constructor for keys (e.g., String, Number) or a custom compare function for keys.
     * @param valueTypeConstructor Expected type constructor for values.
     * @param initial Optional dictionary-like object or iterable of [K,V] pairs to initialize.
     */
    constructor(
        keyTypeOrCompareFn: (new (...args: any[]) => K) | CompareFn<K> | Function, // Function as a broader type for constructors
        valueTypeConstructor: (new (...args: any[]) => V) | Function,
        initial?: Record<string | number, V> | Map<K, V> | Array<[K, V]> | null
    ) {
        this._valueTypeConstructor = valueTypeConstructor;

        let compareFn: CompareFn<K> | undefined;
        if (typeof keyTypeOrCompareFn === 'function' && keyTypeOrCompareFn.length === 2) {
            // It's likely a compare function if it takes two arguments
             compareFn = keyTypeOrCompareFn as CompareFn<K>;
             this._keyTypeConstructor = undefined; // No specific constructor if compareFn is given
        } else {
            this._keyTypeConstructor = keyTypeOrCompareFn as (new (...args: any[]) => K) | Function;
            // Default compareFn will be used by SortedSet if keyType is primitive
        }

        this._keys = new SortedSet<K>([], compareFn); // Pass compareFn if provided
        this._couples = new Map<K, V>();

        if (initial) {
            if (initial instanceof Map) {
                for (const [key, value] of initial) {
                    this.put(key, value);
                }
            } else if (Array.isArray(initial)) { // Array of [K,V] pairs
                 for (const [key, value] of initial) {
                    this.put(key, value);
                }
            } else if (is_dictionary(initial)) { // Record<string|number, V>
                for (const key in initial) {
                    if (Object.prototype.hasOwnProperty.call(initial, key)) {
                        // This type assertion is tricky. If K is not string/number, this might be problematic.
                        // User needs to ensure `initial` keys are compatible with K or provide a Map/Array of pairs.
                        this.put(key as any as K, (initial as Record<string|number,V>)[key]!);
                    }
                }
            }
        }
    }

    static builder<K, V>(
        keyTypeOrCompareFn: (new (...args: any[]) => K) | CompareFn<K> | Function,
        valueTypeConstructor: (new (...args: any[]) => V) | Function
    ): (dictionary?: Record<string | number, V> | Map<K,V> | Array<[K,V]> | null) => SortedDict<K, V> {
        return (dictionary?: Record<string | number, V> | Map<K,V> | Array<[K,V]> | null) =>
            new SortedDict<K, V>(keyTypeOrCompareFn, valueTypeConstructor, dictionary);
    }

    get keyType(): Function | undefined {
        return this._keyTypeConstructor;
    }

    get valueType(): Function {
        return this._valueTypeConstructor;
    }

    toString(): string {
        const items = Array.from(this.items()).map(([k, v]) => `${String(k)}:${String(v)}`).join(', ');
        return `SortedDict{${items}}`;
    }

    get size(): number {
        return this._keys.size;
    }

    public [Symbol.iterator](): IterableIterator<K> {
        return this._keys[Symbol.iterator]();
    }

    equals(other: SortedDict<K, V>): boolean {
        if (!(other instanceof SortedDict)) return false;
        if (this.keyType !== other.keyType || this.valueType !== other.valueType) return false;
        if (this.size !== other.size) return false;

        for (const key of this._keys) {
            if (!other.has(key) || this.get(key) !== other.get(key)) { // Simple equality check for values
                return false;
            }
        }
        return true;
    }

    get(key: K, defaultValue?: V): V | undefined {
        return this._couples.get(key) ?? defaultValue;
    }

    set(key: K, value: V): void {
        // Runtime type check for value (optional, TypeScript handles compile-time)
        // if (this._valueTypeConstructor && !(value instanceof (this._valueTypeConstructor as any))) {
        //     throw new TypeException(this._valueTypeConstructor.name, typeof value);
        // }
        this._keys.add(key);
        this._couples.set(key, value);
    }

    // To align with Map interface and Python's __setitem__
    put(key: K, value: V): void {
        this.set(key, value);
    }

    delete(key: K): V | null {
        if (this._couples.has(key)) {
            this._keys.remove(key);
            const value = this._couples.get(key)!;
            this._couples.delete(key);
            return value;
        }
        return null;
    }

    // To align with Python's remove
    remove(key: K): V | null {
        return this.delete(key);
    }

    has(key: K): boolean {
        return this._couples.has(key);
    }

    firstKey(): K | undefined {
        return this._keys.at(0);
    }

    firstValue(): V | undefined {
        const firstK = this.firstKey();
        return firstK !== undefined ? this._couples.get(firstK) : undefined;
    }

    lastKey(): K | undefined {
        return this._keys.at(this._keys.size - 1);
    }

    lastValue(): V | undefined {
        const lastK = this.lastKey();
        return lastK !== undefined ? this._couples.get(lastK) : undefined;
    }

    lastItem(): [K, V] | undefined {
        const lastK = this.lastKey();
        if (lastK !== undefined) {
            return [lastK, this._couples.get(lastK)!];
        }
        return undefined;
    }

    keys(): IterableIterator<K> {
        return this._keys[Symbol.iterator]();
    }

    *values(): IterableIterator<V> {
        for (const key of this._keys) {
            yield this._couples.get(key)!;
        }
    }

    *reversedValues(): IterableIterator<V> {
        for (const key of this._keys.reversed()) {
            yield this._couples.get(key)!;
        }
    }

    *items(): IterableIterator<[K, V]> {
        for (const key of this._keys) {
            yield [key, this._couples.get(key)!];
        }
    }

    *reversedItems(): IterableIterator<[K,V]> {
        for (const key of this._keys.reversed()) {
            yield [key, this._couples.get(key)!];
        }
    }

    private _get_keys_interval(key_from?: K | null, key_to?: K | null): [number, number] {
        if (this.size === 0) return [0, -1];

        let position_from: number | null;
        if (key_from === null || key_from === undefined) {
            position_from = 0;
        } else {
            position_from = this._keys.indexOf(key_from);
            if (position_from === null) { // key_from not in dict, find next
                const nextKey = this._keys.getNextValue(key_from);
                if (nextKey === null) return [0, -1]; // No key greater than key_from
                position_from = this._keys.indexOf(nextKey);
            }
        }

        let position_to: number | null;
         if (key_to === null || key_to === undefined) {
            position_to = this.size - 1;
        } else {
            position_to = this._keys.indexOf(key_to);
            if (position_to === null) { // key_to not in dict, find previous
                const prevKey = this._keys.getPreviousValue(key_to);
                if (prevKey === null) return [0, -1]; // No key smaller than key_to
                position_to = this._keys.indexOf(prevKey);
            }
        }

        if (position_from === null || position_to === null || position_from > position_to) {
             return [0, -1]; // Invalid interval
        }
        return [position_from, position_to];
    }


    sub_keys(key_from?: K | null, key_to?: K | null): K[] {
        const [pos_from, pos_to] = this._get_keys_interval(key_from, key_to);
        if (pos_from > pos_to) return [];

        const resultKeys: K[] = [];
        let currentIndex = 0;
        for (const key of this._keys) { // Iterate through SortedSet
            if (currentIndex >= pos_from && currentIndex <= pos_to) {
                resultKeys.push(key);
            }
            if (currentIndex > pos_to) break;
            currentIndex++;
        }
        return resultKeys;
    }

    sub(key_from?: K | null, key_to?: K | null): V[] {
        const keys_in_interval = this.sub_keys(key_from, key_to);
        return keys_in_interval.map(key => this._couples.get(key)!);
    }

    remove_sub(key_from?: K | null, key_to?: K | null): void {
        const keys_to_remove = this.sub_keys(key_from, key_to);
        for (const key of keys_to_remove) {
            this.delete(key);
        }
    }

    key_from_index(index: number): K | undefined {
        return this._keys.at(index);
    }

    get_previous_key(key: K): K | null {
        return this._keys.getPreviousValue(key);
    }

    get_next_key(key: K): K | null {
        return this._keys.getNextValue(key);
    }

    clear(): void {
        this._keys.clear();
        this._couples.clear();
    }

    fill(dict?: Record<string | number, V> | Map<K,V> | Array<[K,V]> | null): void {
        if (dict) {
            if (dict instanceof Map) {
                for (const [key, value] of dict) {
                    this.put(key, value);
                }
            } else if (Array.isArray(dict)) {
                 for (const [key, value] of dict) {
                    this.put(key, value);
                }
            } else if (is_dictionary(dict)) {
                for (const key in dict) {
                    if (Object.prototype.hasOwnProperty.call(dict, key)) {
                        this.put(key as any as K, (dict as Record<string|number,V>)[key]!);
                    }
                }
            }
        }
    }

    copy(): SortedDict<K, V> {
        // The constructor of SortedSet needs a compareFn if K is not primitive.
        // This copy method should ideally pass the original compareFn.
        // For now, assuming SortedSet handles this or K is primitive.
        const newDict = new SortedDict<K,V>(
            (this._keys as any).compareFn || this._keyTypeConstructor || String, // Pass compareFn or keyType
            this._valueTypeConstructor
        );
        for (const [key, value] of this.items()) {
            newDict.put(key, value);
        }
        return newDict;
    }
}
