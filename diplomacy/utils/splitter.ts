// diplomacy/utils/splitter.ts
// Contains utils to retrieve splitted subjects fields

export abstract class AbstractStringSplitter {
    protected _input_str: string;
    protected _parts: (string | null)[];
    protected _last_index: number = 0;
    private _length: number;

    constructor(input: string | string[], length: number) {
        this._input_str = Array.isArray(input) ? input.join(' ') : input;
        this._parts = new Array(length).fill(null);
        this._length = length; // Store length for internal use if needed, though _parts.length serves this.
        this._split();
    }

    get input_str(): string {
        return this._input_str;
    }

    get parts(): (string | null)[] {
        return this._parts.slice(0, this._last_index);
    }

    join(): string {
        return this.parts.filter(p => p !== null).join(' ');
    }

    protected abstract _split(): void;

    public getLength(): number { // Equivalent to Python's __len__
        return this._last_index;
    }
}

export class OrderSplitter extends AbstractStringSplitter {
    private _unit_index: number | null = null;
    private _order_type_index: number | null = null;
    private _supported_unit_index: number | null = null;
    private _support_order_type_index: number | null = null;
    private _destination_index: number | null = null;
    private _via_flag_index: number | null = null;

    constructor(input: string | string[]) {
        super(input, 6); // Max 6 parts for an order based on Python example
    }

    get unit(): string | null {
        return this._unit_index !== null ? this._parts[this._unit_index] : null;
    }
    set unit(value: string | null) {
        if (this._unit_index === null) {
            this._unit_index = this._last_index++;
        }
        this._parts[this._unit_index] = value;
    }

    get order_type(): string | null {
        return this._order_type_index !== null ? this._parts[this._order_type_index] : null;
    }
    set order_type(value: string | null) {
        if (this._order_type_index === null) {
            this._order_type_index = this._last_index++;
        }
        this._parts[this._order_type_index] = value;
    }

    get supported_unit(): string | null {
        return this._supported_unit_index !== null ? this._parts[this._supported_unit_index] : null;
    }
    set supported_unit(value: string | null) {
        if (this._supported_unit_index === null) {
            this._supported_unit_index = this._last_index++;
        }
        this._parts[this._supported_unit_index] = value;
    }

    get support_order_type(): string | null {
        return this._support_order_type_index !== null ? this._parts[this._support_order_type_index] : null;
    }
    set support_order_type(value: string | null) {
        if (this._support_order_type_index === null) {
            this._support_order_type_index = this._last_index++;
        }
        this._parts[this._support_order_type_index] = value;
    }

    get destination(): string | null {
        return this._destination_index !== null ? this._parts[this._destination_index] : null;
    }
    set destination(value: string | null) {
        if (this._destination_index === null) {
            this._destination_index = this._last_index++;
        }
        this._parts[this._destination_index] = value;
    }

    get via_flag(): string | null {
        return this._via_flag_index !== null ? this._parts[this._via_flag_index] : null;
    }
    set via_flag(value: string | null) {
        if (this._via_flag_index === null) {
            this._via_flag_index = this._last_index++;
        }
        this._parts[this._via_flag_index] = value;
    }

    protected _split(): void {
        const words = typeof this._input_str === 'string' ? this._input_str.trim().split(/\s+/) : [...this._input_str];

        if (words.length === 1) {
            this.order_type = words.pop()!;
            return;
        }
        if (words.length < 2 && words.length !==1) return; // Not enough parts for a unit

        this.unit = `${words.shift()} ${words.shift()}`;
        if (words.length === 0) { // Implicit hold, e.g. "A PAR"
             this.order_type = "H"; // Default to Hold
             return;
        }

        this.order_type = words.shift()!;

        if (this.order_type === '-' || this.order_type === 'R') { // Move or Retreat
            if (words.length > 0) this.destination = words.shift()!; // Python used pop, which takes from end. Here shift from start.
                                                                  // Order syntax usually is Unit Loc Op Dest ...
        } else if (this.order_type === 'S' || this.order_type === 'C') { // Support or Convoy
            if (words.length >= 2) {
                this.supported_unit = `${words.shift()} ${words.shift()}`;
            }
            if (words.length > 0) {
                this.support_order_type = words.shift()!; // This is actually the '-' for move or target for hold
                if (this.support_order_type === '-') { // Support to move or Convoy
                    if (words.length > 0) this.destination = words.shift()!;
                } else { // Support to Hold, support_order_type is actually the destination
                    this.destination = this.support_order_type;
                    this.support_order_type = null; // No separate support_order_type for S H
                }
            }
        }
        // Build 'B' and Disband 'D' orders are simpler: Unit Loc Op
        // e.g. A PAR B. Unit: A PAR, Op: B. No other parts needed typically by this splitter.
        // The Python version's examples show this structure.

        if (words.length > 0 && words[words.length -1 ] === 'VIA') { // Check last remaining element
            this.via_flag = words.pop()!;
        }
    }
}

export class PhaseSplitter extends AbstractStringSplitter {
    private _season_index: number | null = null;
    private _year_index: number | null = null;
    private _phase_type_index: number | null = null;

    constructor(input: string) { // Phase string like S1901M
        super(input, 3);
    }

    get season(): string | null {
        return this._season_index !== null ? this._parts[this._season_index] : null;
    }
    set season(value: string | null) {
        if (this._season_index === null) this._season_index = this._last_index++;
        this._parts[this._season_index] = value;
    }

    get year(): number | null {
        const val = this._year_index !== null ? this._parts[this._year_index] : null;
        return val !== null ? parseInt(val, 10) : null;
    }
    set year(value: number | null) {
        if (this._year_index === null) this._year_index = this._last_index++;
        this._parts[this._year_index] = value !== null ? String(value) : null;
    }

    get phase_type(): string | null {
        return this._phase_type_index !== null ? this._parts[this._phase_type_index] : null;
    }
    set phase_type(value: string | null) {
        if (this._phase_type_index === null) this._phase_type_index = this._last_index++;
        this._parts[this._phase_type_index] = value;
    }

    protected _split(): void {
        if (this._input_str && this._input_str.length >= 4) { // e.g. S1901M (min length)
            this.season = this._input_str[0];
            // Year can be 2 digits (01) or 4 digits (1901)
            // The Python code `int(self._input_str[1:-1])` implies year is everything between first and last char.
            const yearMatch = this._input_str.substring(1, this._input_str.length -1).match(/\d+/);
            if (yearMatch) {
                 this.year = parseInt(yearMatch[0], 10);
            } else {
                // Handle error or default if year is not found, e.g. for "FORMING"
                this.year = null;
            }
            this.phase_type = this._input_str[this._input_str.length - 1];
        } else {
            // Handle cases like "FORMING", "COMPLETED" or invalid short strings
            // For "FORMING" or "COMPLETED", specific setters might not be called.
            // This splitter is primarily for seasonal phases.
            // To make it robust for "FORMING", etc., we could set one part:
            if (this._input_str === "FORMING" || this._input_str === "COMPLETED") {
                this.phase_type = this._input_str; // Or season, depending on desired output
            }
        }
    }
}
