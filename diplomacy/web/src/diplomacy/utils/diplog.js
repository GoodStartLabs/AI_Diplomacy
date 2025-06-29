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
/*eslint no-console: ["error", {allow: ["log", "info", "warn", "error"]}] */
export class Diplog {
    static error(msg) {
        console.error(msg);
    }

    static warn(msg) {
        console.warn(msg);
    }

    static info(msg) {
        console.log(msg);
    }

    static success(msg) {
        console.log(msg);
    }

    static printMessages(messages) {
        if (messages) {
            if (messages.error)
                Diplog.error(messages.error);
            if (messages.info)
                Diplog.info(messages.info);
            if (messages.success)
                Diplog.success(messages.success);
        }
    }
}
