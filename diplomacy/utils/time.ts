// ==============================================================================
// Copyright (C) 2019 - Philip Paquette
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

/**
 * Time functions
 * - Contains generic time functions (e.g. to calculate deadlines)
 */
import { utcToZonedTime, zonedToUtc } from 'date-fns-tz';
import { getUnixTime, fromUnixTime, getHours, getMinutes, getSeconds, differenceInSeconds } from 'date-fns';

/**
 * Converts a time in format 00W00D00H00M00S in number of seconds
 * @param offsetStr The string to convert (e.g. '20D')
 * @returns Its equivalent in seconds = 1728000
 */
export function strToSeconds(offsetStr: string): number {
    const mult: { [key: string]: number } = { 'W': 7 * 24 * 60 * 60, 'D': 24 * 60 * 60, 'H': 60 * 60, 'M': 60, 'S': 1, ' ': 1 };
    let buffer = 0;
    let currentSum = 0;
    const str = String(offsetStr);

    for (const char of str) {
        if (char >= '0' && char <= '9') {
            buffer = buffer * 10 + parseInt(char, 10);
        } else if (char.toUpperCase() in mult) {
            currentSum += buffer * mult[char.toUpperCase()];
            buffer = 0;
        } else {
            buffer = 0;
        }
    }
    currentSum += buffer;
    return currentSum;
}

function getMidnightTsReference(): number {
    const serverNow = new Date();
    const midnightUtcOfServerCurrentDay = new Date(Date.UTC(
        serverNow.getUTCFullYear(),
        serverNow.getUTCMonth(),
        serverNow.getUTCDate(),
        0, 0, 0, 0
    ));
    return getUnixTime(midnightUtcOfServerCurrentDay);
}

/**
 * Truncates time at a specific interval (e.g. 20M) (i.e. Rounds to the next :20, :40, :60)
 *
 * Note: The reference "day" for truncation (midnight_ts) is based on the server's current UTC day,
 *       matching the behavior of Python's `datetime.date.today()` in the original script.
 *
 * @param timestamp The unix epoch to truncate (e.g. 1498746120)
 * @param truncInterval The truncation interval (e.g. 60*60 or '1H')
 * @param timeZone The time to use for conversion (defaults to GMT otherwise, which is UTC)
 * @returns A timestamp truncated to the nearest (future) interval
 */
export function truncTime(timestamp: number, truncInterval: string | number, timeZone: string = 'GMT'): number {
    const intervalSeconds = typeof truncInterval === 'string' ? strToSeconds(truncInterval) : truncInterval;
    if (intervalSeconds === 0) return timestamp;

    const originalDateUtc = fromUnixTime(timestamp);
    const zonedDate = timeZone === 'GMT' ? originalDateUtc : utcToZonedTime(originalDateUtc, timeZone);

    const zonedDateAsUtc = zonedToUtc(zonedDate, timeZone);
    const tzOffsetSeconds = differenceInSeconds(zonedDate, zonedDateAsUtc);

    const midnightTsRef = getMidnightTsReference();
    const rawMidnightOffset = timestamp - midnightTsRef;
    const midnightOffset = ((rawMidnightOffset % (24 * 3600)) + (24 * 3600)) % (24 * 3600); // JS modulo fix for negatives

    const truncOffset = Math.ceil((midnightOffset + tzOffsetSeconds) / intervalSeconds) * intervalSeconds;
    const truncTs = timestamp - midnightOffset + truncOffset - tzOffsetSeconds;

    return Math.floor(truncTs);
}


/**
 * Returns the next timestamp at a specific 'hh:mm'
 *
 * Note: The reference "day" (midnight_ts) is based on the server's current UTC day,
 *       matching the behavior of Python's `datetime.date.today()` in the original script.
 *
 * @param timestamp The unix timestamp to convert
 * @param timeAt The next 'hh:mm' to have the time rounded to (e.g., "14:30"), or a string compatible with strToSeconds, or 0 to skip
 * @param timeZone The time to use for conversion (defaults to GMT otherwise, which is UTC)
 * @returns A timestamp at the nearest (future) hh:mm
 */
export function nextTimeAt(timestamp: number, timeAt: string | number, timeZone: string = 'GMT'): number {
    if (!timeAt && timeAt !== 0) { // Allow 0 as a valid input for timeAt if it means 0 seconds past midnight
        return timestamp;
    }

    let targetSecondsPastMidnightRef: number;
    if (typeof timeAt === 'string' && timeAt.includes(':')) {
        const parts = timeAt.split(':');
        const hours = parseInt(parts[0], 10);
        const minutes = parseInt(parts[1], 10);
        targetSecondsPastMidnightRef = hours * 3600 + minutes * 60;
    } else if (typeof timeAt === 'string') {
        targetSecondsPastMidnightRef = strToSeconds(timeAt);
    } else { // number
        targetSecondsPastMidnightRef = timeAt;
    }

    // Normalize targetSecondsPastMidnightRef to be within a 0 to 24*3600 range
    // This mirrors the Python logic's effective behavior with modulo in `at_offset` calculation.
    if (targetSecondsPastMidnightRef < 0 || targetSecondsPastMidnightRef >= 24 * 3600) {
        targetSecondsPastMidnightRef = ((targetSecondsPastMidnightRef % (24 * 3600)) + (24 * 3600)) % (24 * 3600);
    }

    const originalDateUtc = fromUnixTime(timestamp);
    const zonedDate = timeZone === 'GMT' ? originalDateUtc : utcToZonedTime(originalDateUtc, timeZone);

    const zonedDateAsUtc = zonedToUtc(zonedDate, timeZone);
    const tzOffsetSeconds = differenceInSeconds(zonedDate, zonedDateAsUtc);

    const midnightTsRef = getMidnightTsReference();
    const rawMidnightOffset = timestamp - midnightTsRef;
    const midnightOffset = ((rawMidnightOffset % (24 * 3600)) + (24 * 3600)) % (24 * 3600); // JS modulo fix

    // Python: at_offset = (-midnight_offset + interval - tz_offset) % (24 * 3600)
    // interval here is targetSecondsPastMidnightRef
    let atOffset = (-midnightOffset + targetSecondsPastMidnightRef - tzOffsetSeconds);
    atOffset = ((atOffset % (24*3600)) + (24*3600)) % (24*3600);

    // at_ts = timestamp + at_offset (Python)
    // The at_offset is the duration to add to the current timestamp's position *within the server's current day structure*
    // to reach the target time.
    // The Python code is: timestamp + ((- ( (timestamp - midnight_UTC_server_day_start) % 86400 ) + target_time_of_day_seconds - tz_offset_seconds) % 86400 )
    // This seems to calculate an offset to add to the original timestamp to hit the target time of day.
    // The crucial part is that `at_offset` is calculated based on `midnight_offset` which is `timestamp` relative to `midnightTsRef` (server's current day).
    // So, `at_offset` is the duration to add to `timestamp` to get it to the desired `time_at` in the context of the `time_zone`,
    // ensuring it's the *next* occurrence.

    const atTs = timestamp + atOffset;

    // If atTs is still behind timestamp (e.g. target time was 10:00, current is 11:00, at_offset might be -1h)
    // then we need to add a day. The modulo arithmetic in Python's at_offset handles this implicitly.
    // If (target_seconds_in_day - current_seconds_in_day_for_timestamp) is negative, it means target is "earlier" today.
    // Python's % (24*3600) makes it positive, effectively pushing it to the "next day" if needed.
    // My atOffset calculation with ((X % M) + M) % M ensures it's a positive offset to add.
    // Let's test:
    // timestamp = 11:00. target_time_of_day = 10:00. tz_offset=0. midnight_offset for 11:00 is 11*3600.
    // at_offset = (-(11*3600) + (10*3600) - 0) = -3600.
    // at_offset_mod = ((-3600 % 86400) + 86400) % 86400 = (-3600 + 86400) % 86400 = 82800. (23 hours)
    // So, 11:00 + 23 hours = 10:00 next day. This is correct.

    return Math.floor(atTs);
}
