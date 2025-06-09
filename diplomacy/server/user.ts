// diplomacy/server/user.ts

import { USERNAME, PASSWORD_HASH, CLIENT_NAME, CLIENT_VERSION, PASSCODE } from '../utils/strings'; // Assuming strings.ts path
import { extend_model, OptionalValueType, ParserType } from '../utils/parsing'; // Assuming parsing.ts path
import { is_valid_password } from '../utils/common'; // Assuming common.ts path and is_valid_password function
import { Jsonable, JsonableModel } from '../utils/jsonable'; // Assuming jsonable.ts path

export class User extends Jsonable {
    public username: string | null = null;
    public password_hash: string | null = null;

    public static override model: JsonableModel = {
        [USERNAME]: ParserType.STR,
        [PASSWORD_HASH]: ParserType.STR,
    };

    constructor(kwargs: Partial<User> = {}) {
        super(kwargs);
        this.username = kwargs.username === undefined ? null : kwargs.username;
        this.password_hash = kwargs.password_hash === undefined ? null : kwargs.password_hash;
    }

    /**
     * Return True if given password matches user hashed password.
     */
    public is_valid_password(password: string): boolean {
        if (!this.password_hash || !password) {
            return false;
        }
        return is_valid_password(password, this.password_hash);
    }

    // Convenience method to set a new password (hashes and stores it)
    // This was not explicitly in the Python User class __init__ but is useful.
    // Requires hash_password to be available and imported from common.ts
    /*
    async set_password(password: string, commonUtils: { hash_password: (pwd: string) => Promise<string> }): Promise<void> {
        if (!is_strong_password(password)) { // Assuming is_strong_password also in common.ts
            throw new Error("Password is not strong enough.");
        }
        this.password_hash = await commonUtils.hash_password(password);
    }
    */
}

export class DaideUser extends User {
    public client_name: string = '';
    public client_version: string = '';
    public passcode: number | null = 0; // Default to 0 as in Python, null if not present

    public static override model: JsonableModel = extend_model(User.model, {
        [CLIENT_NAME]: ParserType.STR,
        [CLIENT_VERSION]: ParserType.STR,
        [PASSCODE]: new OptionalValueType(ParserType.INT),
    });

    constructor(kwargs: Partial<DaideUser> = {}) {
        super(kwargs);
        this.client_name = kwargs.client_name === undefined ? '' : kwargs.client_name;
        this.client_version = kwargs.client_version === undefined ? '' : kwargs.client_version;
        this.passcode = kwargs.passcode === undefined ? 0 : kwargs.passcode;
    }
}
