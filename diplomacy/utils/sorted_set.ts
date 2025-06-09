// diplomacy/utils/sorted_set.ts
// Sorted set implementation.

import { TypeException } from './exceptions'; // Assuming TypeException is defined
import { is_sequence } from './common'; // Assuming is_sequence is defined

export class SortedSet<T> {
    private list: T[] = [];
    private compareFn: (a: T, b: T) => number;

    /**
     * Initialize a typed sorted set.
     * @param content Optional. Sequence of values to initialize sorted set with.
     * @param compareFn Optional. A custom comparison function.
     *                  Defaults to basic <, >, === comparison suitable for numbers and strings.
     *                  For objects, a custom compareFn is highly recommended.
     */
    constructor(content?: Iterable<T>, compareFn?: (a: T, b: T) => number) {
        this.compareFn = compareFn || SortedSet.defaultCompareFn;

        if (content) {
            if (!is_sequence(content) && typeof (content as any)[Symbol.iterator] !== 'function') {
                throw new TypeException('Iterable', typeof content);
            }
            for (const element of content) {
                this.add(element);
            }
        }
    }

    private static defaultCompareFn<T>(a: T, b: T): number {
        if (a < b) return -1;
        if (a > b) return 1;
        return 0;
    }

    /**
     * Find insertion point for x in a to maintain sorted order.
     * If x is already present in a, the insertion point will be before (to the left of) any existing entries.
     * @param value The value to find insertion point for.
     * @returns The index where value should be inserted.
     */
    private _bisect_left(value: T): number {
        let low = 0;
        let high = this.list.length;
        while (low < high) {
            const mid = Math.floor((low + high) / 2);
            if (this.compareFn(this.list[mid]!, value) < 0) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        return low;
    }

    /**
     * Find insertion point for x in a to maintain sorted order.
     * If x is already present in a, the insertion point will be after (to the right of) any existing entries.
     * @param value The value to find insertion point for.
     * @returns The index where value should be inserted.
     */
    private _bisect_right(value: T): number {
        let low = 0;
        let high = this.list.length;
        while (low < high) {
            const mid = Math.floor((low + high) / 2);
            if (this.compareFn(value, this.list[mid]!) < 0) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        return low;
    }

    static builder<T>(compareFn?: (a: T, b: T) => number): (iterable?: Iterable<T>) => SortedSet<T> {
        return (iterable?: Iterable<T>) => new SortedSet<T>(iterable, compareFn);
    }

    toString(): string {
        return `SortedSet(${this.list.map(String).join(', ')})`;
    }

    get size(): number {
        return this.list.length;
    }

    equals(other: SortedSet<T>): boolean {
        if (!(other instanceof SortedSet)) return false;
        if (this.size !== other.size) return false;
        // Assuming same compareFn implies structural equality for this check.
        // A stricter check might involve comparing compareFn references if that's critical.
        for (let i = 0; i < this.list.length; i++) {
            if (this.compareFn(this.list[i]!, other.list[i]!) !== 0) {
                return false;
            }
        }
        return true;
    }

    at(index: number): T | undefined {
        return this.list[index];
    }

    [Symbol.iterator](): IterableIterator<T> {
        return this.list[Symbol.iterator]();
    }

    *reversed(): IterableIterator<T> {
        for (let i = this.list.length - 1; i >= 0; i--) {
            yield this.list[i]!;
        }
    }

    has(element: T): boolean {
        if (this.list.length === 0) return false;
        const position = this._bisect_left(element);
        return position < this.list.length && this.compareFn(this.list[position]!, element) === 0;
    }

    add(element: T): number | undefined {
        const position = this._bisect_left(element);
        if (position === this.list.length || this.compareFn(this.list[position]!, element) !== 0) {
            this.list.splice(position, 0, element);
            return position;
        }
        return undefined; // Element already exists
    }

    getNextValue(element: T): T | null {
        if (this.list.length === 0) return null;
        const position = this._bisect_right(element);
        if (position < this.list.length) {
            // If element itself is present, bisect_right gives the index after it.
            // If element is not present, bisect_right gives the index where it would be inserted (i.e., the next greater element).
            return this.list[position]!;
        }
        return null;
    }

    getPreviousValue(element: T): T | null {
        if (this.list.length === 0) return null;
        const position = this._bisect_left(element);
        if (position > 0) {
            return this.list[position - 1]!;
        }
        return null;
    }

    pop(index: number): T | undefined {
        if (index < 0 || index >= this.list.length) return undefined;
        return this.list.splice(index, 1)[0];
    }

    remove(element: T): T | null {
        const position = this._bisect_left(element);
        if (position < this.list.length && this.compareFn(this.list[position]!, element) === 0) {
            return this.list.splice(position, 1)[0];
        }
        return null;
    }

    indexOf(element: T): number | null {
        const position = this._bisect_left(element);
        if (position < this.list.length && this.compareFn(this.list[position]!, element) === 0) {
            return position;
        }
        return null;
    }

    clear(): void {
        this.list = [];
    }

    // --- Set operations ---
    // These will return new SortedSet instances. They assume 'other' is also a SortedSet.
    // For simplicity, using the default or same compareFn.

    union(other: SortedSet<T>): SortedSet<T> {
        const newSet = new SortedSet<T>([...this.list], this.compareFn);
        for (const elem of other) {
            newSet.add(elem);
        }
        return newSet;
    }

    intersection(other: SortedSet<T>): SortedSet<T> {
        const newSet = new SortedSet<T>([], this.compareFn);
        for (const elem of this.list) {
            if (other.has(elem)) {
                newSet.add(elem);
            }
        }
        return newSet;
    }

    difference(other: SortedSet<T>): SortedSet<T> {
        const newSet = new SortedSet<T>([], this.compareFn);
        for (const elem of this.list) {
            if (!other.has(elem)) {
                newSet.add(elem);
            }
        }
        return newSet;
    }
}
