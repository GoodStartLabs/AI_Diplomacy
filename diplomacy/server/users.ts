// diplomacy/server/users.ts

import { User } from './user';
import {
    USERS, ADMINISTRATORS, TOKEN_TIMESTAMP, TOKEN_TO_USERNAME, USERNAME_TO_TOKENS
} from '../utils/strings'; // Assuming strings.ts path
import {
    ParserType, DictType, SequenceType, JsonableClassType, DefaultValueType
} from '../utils/parsing'; // Assuming parsing.ts path
import { timestamp_microseconds, generate_token } from '../utils/common'; // Assuming common.ts path
import { Jsonable, JsonableModel } from '../utils/jsonable'; // Assuming jsonable.ts path

const TOKEN_LIFETIME_SECONDS = 24 * 60 * 60;

// Placeholder for ConnectionHandler type.
// In a real scenario, this would be a more specific type/interface from the networking layer.
type ConnectionHandler = object;

export class Users extends Jsonable {
    public users: Map<string, User>;
    public administrators: Set<string>;
    public token_timestamp: Map<string, number>; // token -> timestamp
    public token_to_username: Map<string, string>; // token -> username
    public username_to_tokens: Map<string, Set<string>>; // username -> Set<token>

    // In-memory only, not part of the persisted model
    public token_to_connection_handler: Map<string, ConnectionHandler>; // token -> ConnectionHandler
    public connection_handler_to_tokens: Map<ConnectionHandler, Set<string>>; // ConnectionHandler -> Set<token>

    public static override model: JsonableModel = {
        [USERS]: new DefaultValueType(new DictType(ParserType.STR, new JsonableClassType(User)), () => new Map()),
        [ADMINISTRATORS]: new DefaultValueType(new SequenceType(ParserType.STR, () => new Set<string>()), () => new Set()),
        [TOKEN_TIMESTAMP]: new DefaultValueType(new DictType(ParserType.STR, ParserType.INT), () => new Map()),
        [TOKEN_TO_USERNAME]: new DefaultValueType(new DictType(ParserType.STR, ParserType.STR), () => new Map()),
        [USERNAME_TO_TOKENS]: new DefaultValueType(new DictType(ParserType.STR, new SequenceType(ParserType.STR, () => new Set<string>())), () => new Map()),
    };

    constructor(kwargs: Partial<Users> = {}) {
        super(kwargs);
        this.users = kwargs.users === undefined ? new Map() : kwargs.users;
        this.administrators = kwargs.administrators === undefined ? new Set() : kwargs.administrators;
        this.token_timestamp = kwargs.token_timestamp === undefined ? new Map() : kwargs.token_timestamp;
        this.token_to_username = kwargs.token_to_username === undefined ? new Map() : kwargs.token_to_username;
        this.username_to_tokens = kwargs.username_to_tokens === undefined ? new Map() : kwargs.username_to_tokens;

        this.token_to_connection_handler = new Map<string, ConnectionHandler>();
        this.connection_handler_to_tokens = new Map<ConnectionHandler, Set<string>>();
    }

    public has_username(username: string): boolean {
        return this.users.has(username);
    }

    public has_user(username: string, password?: string): boolean {
        const user = this.users.get(username);
        if (!user) return false;
        return password ? user.is_valid_password(password) : this.has_username(username);
    }

    public has_admin(username: string): boolean {
        return this.administrators.has(username);
    }

    public has_token(token: string): boolean {
        return this.token_to_username.has(token);
    }

    public token_is_alive(token: string): boolean {
        if (this.has_token(token)) {
            const currentTime = timestamp_microseconds();
            const tokenTime = this.token_timestamp.get(token) || 0;
            const elapsedTimeSeconds = (currentTime - tokenTime) / 1000000;
            return elapsedTimeSeconds <= TOKEN_LIFETIME_SECONDS;
        }
        return false;
    }

    public relaunch_token(token: string): void {
        if (this.has_token(token)) {
            this.token_timestamp.set(token, timestamp_microseconds());
        }
    }

    public token_is_admin(token: string): boolean {
        const username = this.get_name(token);
        return username ? this.has_admin(username) : false;
    }

    public count_connections(): number {
        return this.connection_handler_to_tokens.size;
    }

    public get_tokens(username: string): Set<string> {
        return new Set(this.username_to_tokens.get(username) || []);
    }

    public get_name(token: string): string | undefined {
        return this.token_to_username.get(token);
    }

    public get_user(username: string): User | undefined {
        return this.users.get(username);
    }

    public get_connection_handler(token: string): ConnectionHandler | undefined {
        return this.token_to_connection_handler.get(token);
    }

    public add_admin(username: string): void {
        if (!this.users.has(username)) {
            // Or throw error: console.error(`Cannot add admin: User ${username} does not exist.`);
            return;
        }
        this.administrators.add(username);
    }

    public remove_admin(username: string): void {
        this.administrators.delete(username);
    }

    public create_token(): string {
        let token = generate_token();
        while (this.has_token(token)) {
            token = generate_token();
        }
        return token;
    }

    public add_user(username: string, password_hash: string): User {
        // TODO: Consider if password should be hashed here or if pre-hashed is always expected.
        // Python version expects pre-hashed.
        if (this.users.has(username)) {
            throw new Error(`User ${username} already exists.`);
        }
        const user = new User({ username, password_hash });
        this.users.set(username, user);
        return user;
    }

    public replace_user(username: string, new_user: User): void {
        if (!this.users.has(username)) {
            throw new Error(`User ${username} does not exist to be replaced.`);
        }
        this.users.set(username, new_user);
    }

    public remove_user(username: string): void {
        const user = this.users.get(username);
        if (!user) return;

        this.users.delete(username);
        this.remove_admin(username);

        const tokens_to_remove = this.username_to_tokens.get(username) || new Set();
        tokens_to_remove.forEach(token => {
            this.token_timestamp.delete(token);
            this.token_to_username.delete(token);
            const connection_handler = this.token_to_connection_handler.get(token);
            if (connection_handler) {
                this.token_to_connection_handler.delete(token);
                const handler_tokens = this.connection_handler_to_tokens.get(connection_handler);
                if (handler_tokens) {
                    handler_tokens.delete(token);
                    if (handler_tokens.size === 0) {
                        this.connection_handler_to_tokens.delete(connection_handler);
                    }
                }
            }
        });
        this.username_to_tokens.delete(username);
    }

    public remove_connection(connection_handler: ConnectionHandler, remove_tokens: boolean = true): Set<string> | null {
        const tokens = this.connection_handler_to_tokens.get(connection_handler);
        if (tokens) {
            this.connection_handler_to_tokens.delete(connection_handler);
            tokens.forEach(token => {
                this.token_to_connection_handler.delete(token);
                if (remove_tokens) {
                    const username = this.token_to_username.get(token);
                    this.token_timestamp.delete(token);
                    this.token_to_username.delete(token);
                    if (username) {
                        const user_tokens = this.username_to_tokens.get(username);
                        if (user_tokens) {
                            user_tokens.delete(token);
                            if (user_tokens.size === 0) {
                                this.username_to_tokens.delete(username);
                            }
                        }
                    }
                }
            });
            return tokens;
        }
        return null;
    }

    public connect_user(username: string, connection_handler: ConnectionHandler): string {
        const user = this.users.get(username);
        if (!user) {
            throw new Error(`User ${username} not found.`);
        }
        const token = this.create_token();

        this.connection_handler_to_tokens.set(connection_handler,
            (this.connection_handler_to_tokens.get(connection_handler) || new Set()).add(token)
        );
        this.username_to_tokens.set(user.username!,
            (this.username_to_tokens.get(user.username!) || new Set()).add(token)
        );

        this.token_to_username.set(token, user.username!);
        this.token_to_connection_handler.set(token, connection_handler);
        this.token_timestamp.set(token, timestamp_microseconds());
        return token;
    }

    public attach_connection_handler(token: string, connection_handler: ConnectionHandler): void {
        if (this.has_token(token)) {
            const previous_connection = this.get_connection_handler(token);
            if (previous_connection && previous_connection !== connection_handler) {
                 // In Python, this was an assert. Throwing an error is more idiomatic in TS for such conditions.
                throw new Error("A new connection handler cannot be attached to a token already connected to another handler.");
            }
            if (!previous_connection) {
                console.warn('Attaching a new connection handler to a token.'); // Matched Python's LOGGER.warning
                let handler_tokens = this.connection_handler_to_tokens.get(connection_handler);
                if (!handler_tokens) {
                    handler_tokens = new Set<string>();
                    this.connection_handler_to_tokens.set(connection_handler, handler_tokens);
                }
                handler_tokens.add(token);
                this.token_to_connection_handler.set(token, connection_handler);
            }
            // Always update timestamp, even if handler was already attached or is the same.
            this.token_timestamp.set(token, timestamp_microseconds());
        } else {
            console.warn(`Attempted to attach connection handler to unknown token: ${token}`);
        }
    }

    public disconnect_token(token: string): void {
        if (!this.has_token(token)) return;

        this.token_timestamp.delete(token);
        const username = this.token_to_username.get(token);
        this.token_to_username.delete(token);

        if (username) {
            const user_tokens = this.username_to_tokens.get(username);
            if (user_tokens) {
                user_tokens.delete(token);
                if (user_tokens.size === 0) {
                    this.username_to_tokens.delete(username);
                }
            }
        }

        const connection_handler = this.token_to_connection_handler.get(token);
        if (connection_handler) {
            this.token_to_connection_handler.delete(token);
            const handler_tokens = this.connection_handler_to_tokens.get(connection_handler);
            if (handler_tokens) {
                handler_tokens.delete(token);
                if (handler_tokens.size === 0) {
                    this.connection_handler_to_tokens.delete(connection_handler);
                }
            }
        }
    }
}
