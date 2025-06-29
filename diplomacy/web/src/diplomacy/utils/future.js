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
/** Class Future (like Python's Tornado future). **/
export class Future {
    constructor() {
        this.__resolve_fn = null;
        this.__reject_fn = null;
        this.__promise = null;
        this.__done = false;

        const future = this;
        this.__promise = new Promise((resolve, reject) => {
            future.__resolve_fn = resolve;
            future.__reject_fn = reject;
        });
    }

    promise() {
        return this.__promise;
    }

    setResult(result) {
        if (!this.done()) {
            this.__done = true;
            const resolve_fn = this.__resolve_fn;
            resolve_fn(result);
        }
    }

    setException(exception) {
        if (!this.done()) {
            this.__done = true;
            const reject_fn = this.__reject_fn;
            reject_fn(exception);
        }
    }

    done() {
        return this.__done;
    }
}
