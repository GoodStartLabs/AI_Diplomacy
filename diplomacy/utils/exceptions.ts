// diplomacy/utils/exceptions.ts
// Exceptions used in diplomacy code.

export class DiplomacyException extends Error {
    constructor(message: string = 'Diplomacy network code exception.') {
        // Clean up message similar to Python's self.__doc__.strip() if message is empty
        const finalMessage = message || (new.target.prototype.constructor as any).__doc__?.trim() || 'Diplomacy network code exception.';
        super(finalMessage);
        this.name = new.target.name; // Sets the error name to the class name
        // This is important for `instanceof` checks and for more descriptive error logging.
        Object.setPrototypeOf(this, new.target.prototype); // Maintain prototype chain
    }
}

export class AlreadyScheduledException extends DiplomacyException {
    static __doc__ = "Cannot add a data already scheduled.";
    constructor(message?: string) {
        super(message || AlreadyScheduledException.__doc__);
    }
}

export class CommonKeyException extends DiplomacyException {
    static __doc__ = "Common key error.";
    constructor(key: string) {
        super(`Forbidden common key in two dicts (${key})`);
    }
}

export class KeyException extends DiplomacyException {
    static __doc__ = "Key error.";
    constructor(key: string) {
        super(`Key error: ${key}`);
    }
}

export class LengthException extends DiplomacyException {
    static __doc__ = "Length error.";
    constructor(expected_length: number, given_length: number) {
        super(`Expected length ${expected_length}, got ${given_length}.`);
    }
}

export class NaturalIntegerException extends DiplomacyException {
    static __doc__ = "Expected a positive integer (int >= 0).";
    constructor(integer_name: string = '') {
        super(integer_name ? `Integer error: ${integer_name}. ${NaturalIntegerException.__doc__}` : NaturalIntegerException.__doc__);
    }
}

export class NaturalIntegerNotNullException extends NaturalIntegerException {
    static __doc__ = "Expected a strictly positive integer (int > 0).";
     constructor(integer_name: string = '') {
        super(integer_name ? `Integer error: ${integer_name}. ${NaturalIntegerNotNullException.__doc__}` : NaturalIntegerNotNullException.__doc__);
    }
}

export class RandomPowerException extends DiplomacyException {
    static __doc__ = "No enough playable powers to select random powers.";
    constructor(nb_powers: number, nb_available_powers: number) {
        super(`Cannot randomly select ${nb_powers} power(s) in ${nb_available_powers} available power(s).`);
    }
}

export class TypeException extends DiplomacyException {
    static __doc__ = "Type error.";
    constructor(expected_type: string, given_type: string) {
        super(`Expected type ${expected_type}, got type ${given_type}`);
    }
}

export class ValueException extends DiplomacyException {
    static __doc__ = "Value error.";
    constructor(expected_values: any[], given_value: any) {
        super(`Forbidden value ${given_value}, expected: ${expected_values.map(v => String(v)).join(', ')}`);
    }
}

export class NotificationException extends DiplomacyException {
    static __doc__ = "Unknown notification.";
     constructor(message?: string) {
        super(message || NotificationException.__doc__);
    }
}

export class ResponseException extends DiplomacyException {
    static __doc__ = "Unknown response.";
     constructor(message?: string) {
        super(message || ResponseException.__doc__);
    }
}

export class RequestException extends ResponseException {
    static __doc__ = "Unknown request.";
     constructor(message?: string) {
        super(message || RequestException.__doc__);
    }
}

export class AdminTokenException extends ResponseException {
    static __doc__ = "Invalid token for admin operations.";
     constructor(message?: string) {
        super(message || AdminTokenException.__doc__);
    }
}

export class DaidePortException extends ResponseException {
    static __doc__ = "Daide server not started for the game";
     constructor(message?: string) {
        super(message || DaidePortException.__doc__);
    }
}

export class GameCanceledException extends ResponseException {
    static __doc__ = "Game was cancelled.";
     constructor(message?: string) {
        super(message || GameCanceledException.__doc__);
    }
}

export class GameCreationException extends ResponseException {
    static __doc__ = "Cannot create more games on that server.";
    constructor(message?: string) {
        super(message || GameCreationException.__doc__);
    }
}

export class GameFinishedException extends ResponseException {
    static __doc__ = "This game is finished.";
    constructor(message?: string) {
        super(message || GameFinishedException.__doc__);
    }
}

export class GameIdException extends ResponseException {
    static __doc__ = "Invalid game ID.";
    constructor(message?: string) {
        super(message || GameIdException.__doc__);
    }
}

export class GameJoinRoleException extends ResponseException {
    static __doc__ = "A token can have only one role inside a game: player, observer or omniscient.";
    constructor(message?: string) {
        super(message || GameJoinRoleException.__doc__);
    }
}

export class GameRoleException extends ResponseException {
    static __doc__ = "Game role does not accepts this action.";
    constructor(message?: string) {
        super(message || GameRoleException.__doc__);
    }
}

export class GameMasterTokenException extends ResponseException {
    static __doc__ = "Invalid token for master operations.";
    constructor(message?: string) {
        super(message || GameMasterTokenException.__doc__);
    }
}

export class GameNotPlayingException extends ResponseException {
    static __doc__ = "Game not playing.";
    constructor(message?: string) {
        super(message || GameNotPlayingException.__doc__);
    }
}

export class GameObserverException extends ResponseException {
    static __doc__ = "Disallowed observation for non-master users.";
    constructor(message?: string) {
        super(message || GameObserverException.__doc__);
    }
}

export class GamePhaseException extends ResponseException {
    static __doc__ = "Data does not match current game phase.";
    constructor(expected?: string | null, given?: string | null, message?: string) {
        let constructedMessage = message || GamePhaseException.__doc__;
        if (expected !== undefined && expected !== null) { // Allow expected to be null but explicitly passed
            constructedMessage += ` Expected: ${expected}`;
        }
        if (given !== undefined && given !== null) { // Allow given to be null but explicitly passed
            constructedMessage += ` Given: ${given}`;
        }
        super(constructedMessage);
    }
}

export class GamePlayerException extends ResponseException {
    static __doc__ = "Invalid player.";
    constructor(message?: string) {
        super(message || GamePlayerException.__doc__);
    }
}

export class GameRegistrationPasswordException extends ResponseException {
    static __doc__ = "Invalid game registration password.";
    constructor(message?: string) {
        super(message || GameRegistrationPasswordException.__doc__);
    }
}

export class GameSolitaireException extends ResponseException {
    static __doc__ = "A solitaire game does not accepts players.";
    constructor(message?: string) {
        super(message || GameSolitaireException.__doc__);
    }
}

export class GameTokenException extends ResponseException {
    static __doc__ = "Invalid token for this game.";
    constructor(message?: string) {
        super(message || GameTokenException.__doc__);
    }
}

export class MapIdException extends ResponseException {
    static __doc__ = "Invalid map ID.";
    constructor(message?: string) {
        super(message || MapIdException.__doc__);
    }
}

export class MapPowerException extends ResponseException {
    static __doc__ = "Invalid map power.";
    constructor(power_name: string) {
        super(`Invalid map power ${power_name}`);
    }
}

export class FolderException extends ResponseException {
    static __doc__ = "Given folder not available in server.";
    constructor(folder_path: string) {
        super(`Given folder not available in server: ${folder_path}`);
    }
}

export class ServerRegistrationException extends ResponseException {
    static __doc__ = "Registration currently not allowed on this server.";
    constructor(message?: string) {
        super(message || ServerRegistrationException.__doc__);
    }
}

export class TokenException extends ResponseException {
    static __doc__ = "Invalid token.";
    constructor(message?: string) {
        super(message || TokenException.__doc__);
    }
}

export class UserException extends ResponseException {
    static __doc__ = "Invalid user.";
    constructor(message?: string) {
        super(message || UserException.__doc__);
    }
}

export class PasswordException extends ResponseException {
    static __doc__ = "Password must not be empty.";
    constructor(message?: string) {
        super(message || PasswordException.__doc__);
    }
}

export class ServerDirException extends ResponseException {
    static __doc__ = "Error with working folder.";
    constructor(server_dir: string) {
        super(`No server directory available at path ${server_dir}`);
    }
}
