// diplomacy/utils/priority_dict.ts

type HeapEntry<K, V extends number> = [V, K, boolean]; // [priority, key, isValid]

export class PriorityDict<K, V extends number> {
    private heap: Array<HeapEntry<K, V>> = [];
    private entries: Map<K, HeapEntry<K, V>> = new Map();

    constructor(initial?: Record<string | number, V> | Array<[K, V]>) {
        if (initial) {
            if (Array.isArray(initial)) { // Array of [key, priority] tuples
                for (const [key, priority] of initial) {
                    this.set(key, priority);
                }
            } else { // Record object
                for (const key in initial) {
                    if (Object.prototype.hasOwnProperty.call(initial, key)) {
                        // We need to be careful about key type if K is not string or number
                        this.set(key as any as K, initial[key]!);
                    }
                }
            }
        }
    }

    private _siftup(index: number): void {
        let parent = Math.floor((index - 1) / 2);
        while (index > 0 && this.heap[index]![0] < this.heap[parent]![0]) {
            [this.heap[index], this.heap[parent]] = [this.heap[parent]!, this.heap[index]!];
            index = parent;
            parent = Math.floor((index - 1) / 2);
        }
    }

    private _siftdown(index: number): void {
        const N = this.heap.length;
        while (true) {
            let leftChildIdx = 2 * index + 1;
            let rightChildIdx = 2 * index + 2;
            let smallest = index;

            if (leftChildIdx < N && this.heap[leftChildIdx]![0] < this.heap[smallest]![0]) {
                smallest = leftChildIdx;
            }
            if (rightChildIdx < N && this.heap[rightChildIdx]![0] < this.heap[smallest]![0]) {
                smallest = rightChildIdx;
            }

            if (smallest !== index) {
                [this.heap[index], this.heap[smallest]] = [this.heap[smallest]!, this.heap[index]!];
                index = smallest;
            } else {
                break;
            }
        }
    }

    private _heappush(entry: HeapEntry<K, V>): void {
        this.heap.push(entry);
        this._siftup(this.heap.length - 1);
    }

    private _heappop(): HeapEntry<K, V> | undefined {
        if (this.heap.length === 0) {
            return undefined;
        }
        if (this.heap.length === 1) {
            return this.heap.pop();
        }
        const top = this.heap[0];
        this.heap[0] = this.heap.pop()!;
        this._siftdown(0);
        return top;
    }

    set(key: K, priority: V): void {
        if (this.entries.has(key)) {
            const oldEntry = this.entries.get(key)!;
            oldEntry[2] = false; // Mark old entry as invalid
        }
        const newEntry: HeapEntry<K, V> = [priority, key, true];
        this.entries.set(key, newEntry);
        this._heappush(newEntry);
    }

    delete(key: K): boolean {
        if (this.entries.has(key)) {
            const entry = this.entries.get(key)!;
            entry[2] = false; // Mark as invalid
            this.entries.delete(key);
            return true;
        }
        return false;
    }

    get(key: K): V | undefined {
        const entry = this.entries.get(key);
        // Python's __getitem__ raises KeyError if key not found or entry invalid.
        // Here, we return undefined for simplicity, typical in JS/TS Map.get.
        // To strictly match Python, one might throw an error if !entry || !entry[2].
        return (entry && entry[2]) ? entry[0] : undefined;
    }

    has(key: K): boolean {
        const entry = this.entries.get(key);
        return !!(entry && entry[2]);
    }

    get size(): number {
        return this.entries.size;
    }

    isEmpty(): boolean {
        return this.entries.size === 0;
    }

    smallest(): [V, K] | null {
        while (this.heap.length > 0 && !this.heap[0]![2]) { // Check isValid flag
            this._heappop(); // Remove invalid entries from the top
        }
        if (this.heap.length > 0) {
            return [this.heap[0]![0], this.heap[0]![1]]; // [priority, key]
        }
        return null;
    }

    popSmallest(): [V, K] | null {
        let smallestEntry: HeapEntry<K,V> | undefined;
        do {
            smallestEntry = this._heappop();
        } while (smallestEntry && !smallestEntry[2]); // Loop until a valid entry is found or heap is empty

        if (smallestEntry) {
            this.entries.delete(smallestEntry[1]);
            return [smallestEntry[0], smallestEntry[1]];
        }
        return null;
    }

    setDefault(key: K, defaultPriority: V): V {
        if (!this.has(key)) {
            this.set(key, defaultPriority);
        }
        return this.get(key)!; // Should exist now
    }

    copy(): PriorityDict<K, V> {
        const newDict = new PriorityDict<K, V>();
        // Iterate over valid entries in the current dict to maintain priorities
        for (const [key, entry] of this.entries) {
            if (entry[2]) { // if valid
                 newDict.set(key, entry[0]); // entry[0] is priority
            }
        }
        return newDict;
    }

    clear(): void {
        this.heap = [];
        this.entries.clear();
    }

    /** Iterate over keys in priority order. */
    *keys(): IterableIterator<K> {
        const tempCopy = this.copy(); // Use a copy to not modify the original during iteration
        while (!tempCopy.isEmpty()) {
            const smallest = tempCopy.popSmallest();
            if (smallest) {
                yield smallest[1]; // Yield key
            } else {
                break; // Should not happen if isEmpty is false
            }
        }
    }

    /** Iterate over values (priorities) in priority order. */
    *values(): IterableIterator<V> {
        for (const key of this.keys()) {
            yield this.get(key)!; // get(key) returns priority
        }
    }

    /** Iterate over [key, value (priority)] pairs in priority order. */
    *items(): IterableIterator<[K, V]> {
        for (const key of this.keys()) {
            yield [key, this.get(key)!];
        }
    }

    // For compatibility with for...of loops directly on the PriorityDict instance
    [Symbol.iterator](): IterableIterator<K> {
        return this.keys();
    }
}
