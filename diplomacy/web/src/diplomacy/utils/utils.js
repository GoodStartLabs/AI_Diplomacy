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
/** Utils. **/

class Dict {
}

export const UTILS = {
    NB_CONNECTION_ATTEMPTS: 12,
    ATTEMPT_DELAY_SECONDS: 5,
    REQUEST_TIMEOUT_SECONDS: 30,

    /** Return a random integer in interval [from, to). **/
    randomInteger: function (from, to) {
        return Math.floor(Math.random() * (to - from) + from);
    },

    /** Create an ID string using current time + 5 random integers each with 10 digits. **/
    createID: function () {
        let id = new Date().getTime().toString(10);
        for (let i = 0; i < 5; ++i)
            id += UTILS.randomInteger(1e9, 1e10);
        return id;
    },

    createGameID: function (username) {
        return `${username}_${new Date().getTime().toString(10)}`;
    },

    date: function () {
        const d = new Date();
        return d.toLocaleString() + '.' + d.getMilliseconds();
    },

    microsecondsToDate: function (time) {
        return new Date(Math.floor(time / 1000));
    },

    binarySearch: {
        find: function (array, element) {
            let a = 0;
            let b = array.length - 1;
            while (a <= b) {
                const c = Math.floor((a + b) / 2);
                if (array[c] === element)
                    return c;
                if (array[c] < element)
                    a = c + 1;
                else
                    b = c - 1;
            }
            return -1;
        },
        insert: function (array, element) {
            let a = 0;
            let b = array.length - 1;
            while (a <= b) {
                const c = Math.floor((a + b) / 2);
                if (array[c] === element)
                    return c;
                if (array[c] < element)
                    a = c + 1;
                else
                    b = c - 1;
            }
            // If we go out of loop, then array[b] < element, so we must insert element at position b + 1.
            if (b < array.length - 1)
                array.splice(b + 1, 0, element);
            else
                array.push(element);
            return b + 1;
        }
    },

    javascript: {

        arrayIsEmpty: function (array) {
            return !(array && array.length);
        },

        hasArray: function (array) {
            return array && array.length;
        },

        clearObject: function (obj) {
            const keys = Object.keys(obj);
            for (let key of keys)
                delete obj[key];
        },

        /** Create a dictionary from given array, using array elements as dictionary values
         * and array elements's `field` values (element[field]) as dictionary keys. **/
        arrayToDict: function (array, field) {
            const dictionary = {};
            for (let entry of array)
                dictionary[entry[field]] = entry;
            return dictionary;
        },

        count(obj) {
            return Object.keys(obj).length;
        },

        extendArrayWithUniqueValues(obj, key, value) {
            if (!obj.hasOwnProperty(key))
                obj[key] = [value];
            else if (!obj[key].includes(value))
                obj[key].push(value);
        },

        extendTreeValue: function (obj, path, value, allowMultipleValues) {
            let current = obj;
            const pathLength = path.length;
            const parentPathLength = pathLength - 1;
            for (let i = 0; i < parentPathLength; ++i) {
                const stepName = path[i];
                if (!current.hasOwnProperty(stepName))
                    current[stepName] = new Dict();
                current = current[stepName];
            }
            const stepName = path[pathLength - 1];
            if (!current.hasOwnProperty(stepName))
                current[stepName] = [];
            if (allowMultipleValues || !current[stepName].includes(value))
                current[stepName].push(value);
        },

        getTreeValue: function (obj, path) {
            let current = obj;
            for (let stepName of path) {
                if (!current.hasOwnProperty(stepName))
                    return null;
                current = current[stepName];
            }
            if (current instanceof Dict)
                return Object.keys(current);
            return current;
        }
    },

    html: {

        // Source: https://www.w3schools.com/charsets/ref_utf_geometric.asp
        UNICODE_LEFT_ARROW: '\u25C0',
        UNICODE_RIGHT_ARROW: '\u25B6',
        UNICODE_TOP_ARROW: '\u25BC',
        UNICODE_BOTTOM_ARROW: '\u25B2',
        CROSS: '\u00D7',
        UNICODE_SMALL_RIGHT_ARROW: '\u2192',
        UNICODE_SMALL_LEFT_ARROW: '\u2190',

        isSelect: function (element) {
            return element.tagName.toLowerCase() === 'select';
        },

        isInput: function (element) {
            return element.tagName.toLowerCase() === 'input';
        },

        isCheckBox: function (element) {
            return UTILS.html.isInput(element) && element.type === 'checkbox';
        },

        isRadioButton: function (element) {
            return UTILS.html.isInput(element) && element.type === 'radio';
        },

        isTextInput: function (element) {
            return UTILS.html.isInput(element) && element.type === 'text';
        },

        isPasswordInput: function (element) {
            return UTILS.html.isInput(element) && element.type === 'password';
        }

    }

};
