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
import {Future} from "./future";

export class Queue {
    constructor() {
        this.future = new Future();
        this.queue = [];
        this.append = this.append.bind(this);
        this.get = this.get.bind(this);
        this.consume = this.consume.bind(this);
    }

    append(value) {
        this.queue.push(value);
        if (this.queue.length - 1 === 0) {
            const previousFuture = this.future;
            previousFuture.setResult(null);
            this.future = new Future();
        }
    }

    __next_value() {
        return this.queue.length ? this.queue.shift() : null;
    }

    get() {
        return new Promise(resolve => {
            if (this.queue.length) {
                resolve(this.__next_value());
            } else {
                this.future.promise().then(() => resolve(this.__next_value()));
            }
        });
    }

    consume(valueConsumer) {
        const recursiveConsumer = (value) => {
            if (value !== null) {
                valueConsumer(value);
                this.get().then(recursiveConsumer);
            }
        };
        this.get().then(recursiveConsumer);
    }

    consumeAsync(valueConsumer) {
        const recursiveConsumer = (value) => {
            if (value !== null) {
                valueConsumer(value)
                    .then(() => this.get())
                    .then(recursiveConsumer);
            }
        };
        this.get().then(recursiveConsumer);
    }
}
