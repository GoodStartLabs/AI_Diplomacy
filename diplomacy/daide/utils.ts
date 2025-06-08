// diplomacy/daide/utils.ts

import { Token, isIntegerToken } from './tokens'; // Assuming tokens.ts is in the same directory

// Logger (optional)
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// --- Placeholders for server-side and game engine types ---
interface DaideUser { // Placeholder for server_users.users.get() return type
    // Define properties of a DAIDE user if known, e.g., username, id, etc.
    [key: string]: any;
}

interface ServerUsers { // Placeholder for diplomacy.server.users
    get_name(token: string): string | null;
    has_token(token: string): boolean;
    users: Record<string, DaideUser | undefined>; // username -> DaideUser
}

interface PowerDetails { // Placeholder for game.powers[power_name]
    is_controlled_by(username: string | null): boolean;
    // other power properties
}

interface DiplomacyGame { // Placeholder for diplomacy.engine.game.Game
    powers: Record<string, PowerDetails>; // power_name -> PowerDetails
    // other game properties
}

interface ConnectionHandler { // Placeholder for connection_handler argument
    token: string;
    // other connection handler properties
}


// Equivalent to Python's namedtuple ClientConnection
export interface ClientConnectionInfo {
    username: string | null;
    daide_user: DaideUser | null | undefined;
    token: string;
    power_name: string | null;
}

export function get_user_connection(
    server_users: ServerUsers,
    game: DiplomacyGame,
    connection_handler: ConnectionHandler
): ClientConnectionInfo {
    const token = connection_handler.token;
    const username = server_users.has_token(token) ? server_users.get_name(token) : null;
    const daide_user = username ? server_users.users[username] : undefined;

    let power_name: string | null = null;
    if (username && game && game.powers) {
        const user_powers = Object.entries(game.powers)
            .filter(([_, power_obj]) => power_obj.is_controlled_by(username))
            .map(([p_name, _]) => p_name);
        power_name = user_powers.length > 0 ? user_powers[0] : null;
    }

    return { username, daide_user, token, power_name };
}

export function daideStringToBytes(daide_str: string): Uint8Array {
    const buffer: Uint8Array[] = [];
    const str_split = daide_str ? daide_str.split(' ') : [];

    for (const word of str_split) {
        if (word === '') {
            // In Python, this was bytes(Token(from_str=' ')).
            // This implies a space token if an empty string segment is produced by split,
            // which can happen with multiple spaces, e.g. "A  B" -> ["A", "", "B"].
            // A single space token might be needed if the protocol expects it.
            // For now, let's assume empty words from split are ignored or handled if a specific space token exists.
            // If DAIDE has an explicit space token, it should be registered in tokens.ts.
            // Python `bytes(Token(from_str=' '))` would create an ASCII token for space.
             try {
                buffer.push(new Token({ from_str: ' ' }).toBytes());
            } catch (e) {
                logger.warn("Space token not registered or failed to create, skipping empty word from split.");
            }
        } else if (word.startsWith('#')) {
            try {
                const num = parseInt(word.substring(1), 10);
                if (isNaN(num)) throw new Error(`Invalid number: ${word}`);
                buffer.push(new Token({ from_int: num }).toBytes());
            } catch (e: any) {
                logger.error(`Error parsing integer token "${word}": ${e.message}`);
                // Decide on error handling: throw, or push a default/error token, or skip
            }
        } else {
            try {
                buffer.push(new Token({ from_str: word }).toBytes());
            } catch (e: any) {
                logger.error(`Error parsing string token "${word}": ${e.message}`);
                // Decide on error handling
            }
        }
    }

    // Concatenate all Uint8Arrays in the buffer
    let totalLength = 0;
    for (const arr of buffer) {
        totalLength += arr.length;
    }
    const result = new Uint8Array(totalLength);
    let offset = 0;
    for (const arr of buffer) {
        result.set(arr, offset);
        offset += arr.length;
    }
    return result;
}

export function daideBytesToString(daide_bytes: Uint8Array | null): string {
    if (!daide_bytes) {
        return "";
    }

    const buffer: string[] = [];
    const length = daide_bytes.length;

    for (let i = 0; i < length; i += 2) {
        if (i + 1 >= length) {
            logger.error("Invalid DAIDE byte sequence: odd number of bytes.");
            break; // Or throw error
        }
        const byte_pair = daide_bytes.slice(i, i + 2);
        try {
            const token = new Token({ from_bytes: byte_pair });
            if (isIntegerToken(token)) {
                buffer.push('#' + token.toString());
            } else {
                buffer.push(token.toString());
            }
        } catch (e: any) {
            logger.error(`Error parsing byte pair ${byte_pair[0]},${byte_pair[1]}: ${e.message}`);
            // Decide on error handling: throw, or push an error marker, or skip
        }
    }
    return buffer.join(' ');
}
