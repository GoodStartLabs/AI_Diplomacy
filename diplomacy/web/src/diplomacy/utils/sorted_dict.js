// ==============================================================================
// Copyright (C) 2019 - Philip Paquette, Steven Bocco
//
//  This program is free software: you can redistribute it and/or modify it under
//  the terms of the GNU Affero General Public License as published by the Free
//  Software Foundation, either version 3 of the License, or (at your option) any
//  later version.
//
//  This program is distributed in the hope that it will be useful, but WITHOUT
//  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
//  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
//  details.
//
//  You should have received a copy of the GNU Affero General Public License along
//  with this program.  If not, see <https://www.gnu.org/licenses/>.
// ==============================================================================
import {UTILS} from "./utils";

function defaultComparableKey(key) {
    return key;
}

export class SortedDict {
    constructor(dct, keyFn) {
        this.__real_keys = [];
        this.__keys = [];
        this.__values = [];
        this.__key_fn = keyFn || defaultComparableKey;
        if (dct) for (let key of Object.keys(dct))
            this.put(key, dct[key]);
    }

    clear() {
        this.__real_keys = [];
        this.__keys = [];
        this.__values = [];
    }

    put(key, value) {
        const realKey = key;
        key = this.__key_fn(key);
        const position = UTILS.binarySearch.insert(this.__keys, key);
        if (position === this.__values.length) {
            this.__values.push(value);
            this.__real_keys.push(realKey);
        } else if (this.__values[position] !== value) {
            this.__values.splice(position, 0, value);
            this.__real_keys.splice(position, 0, realKey);
        }
        return position;
    }

    remove(key) {
        key = this.__key_fn(key);
        const position = UTILS.binarySearch.find(this.__keys, key);
        if (position < 0)
            return null;
        this.__keys.splice(position, 1);
        this.__real_keys.splice(position, 1);
        return this.__values.splice(position, 1)[0];
    }

    contains(key) {
        return UTILS.binarySearch.find(this.__keys, this.__key_fn(key)) >= 0;
    }

    get(key) {
        const position = UTILS.binarySearch.find(this.__keys, this.__key_fn(key));
        if (position < 0)
            return null;
        return this.__values[position];
    }

    indexOf(key) {
        return UTILS.binarySearch.find(this.__keys, this.__key_fn(key));
    }

    keyFromIndex(index) {
        return this.__real_keys[index];
    }

    valueFromIndex(index) {
        return this.__values[index];
    }

    size() {
        return this.__keys.length;
    }

    lastKey() {
        if (!this.__keys.length)
            throw new Error('Sorted dict is empty.');
        return this.__real_keys[this.__keys.length - 1];
    }

    lastValue() {
        if (!this.__keys.length)
            throw new Error('Sorted dict is empty.');
        return this.__values[this.__values.length - 1];
    }

    keys() {
        return this.__real_keys.slice();
    }

    values() {
        return this.__values.slice();
    }

    toDict() {
        const len = this.__real_keys.length;
        const dict = {};
        for (let i = 0; i < len; ++i) {
            dict[this.__real_keys[i]] = this.__values[i];
        }
        return dict;
    }
}
