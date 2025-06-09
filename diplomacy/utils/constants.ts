// diplomacy/utils/constants.ts
// Some constant / config values used in Diplomacy package.

// Number of times to try to connect before throwing an exception.
export const NB_CONNECTION_ATTEMPTS = 12;

// Time to wait between to connection trials.
export const ATTEMPT_DELAY_SECONDS = 5;

// Time to wait between to server backups.
export const DEFAULT_BACKUP_DELAY_SECONDS = 10 * 60; // 10 minutes.

// Default server ping interval. // Used for sockets ping.
export const DEFAULT_PING_SECONDS = 30;

// Time to wait to receive a response for a request sent to server.
export const REQUEST_TIMEOUT_SECONDS = 30;

// Default host name for a server to connect to.
export const DEFAULT_HOST = 'localhost';

// Default port for normal non-securized server.
export const DEFAULT_PORT = 8432;

// Default port for secure SSL server (not yet used).
export const DEFAULT_SSL_PORT = 8433;

// Special username and password to use to connect as a bot recognized by diplomacy module.
// This bot is called "private bot".
export const PRIVATE_BOT_USERNAME = '#bot@2e723r43tr70fh2239-qf3947-3449-21128-9dh1321d12dm13d83820d28-9dm,xw201=ed283994f4n832483';
export const PRIVATE_BOT_PASSWORD = '#bot:password:28131821--mx1fh5g7hg5gg5g´[],s222222223djdjje399333x93901deedd|e[[[]{{|@S{@244f';

// Time to wait to let a bot set orders for a dummy power.
export const PRIVATE_BOT_TIMEOUT_SECONDS = 60;

// Default rules used to construct a Game object when no rules are provided.
export const DEFAULT_GAME_RULES: string[] = ['SOLITAIRE', 'NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'];

/**
 * Constants to define flags for attribute Power.order_is_set.
 */
export enum OrderSettings {
    ORDER_NOT_SET = 0,
    ORDER_SET_EMPTY = 1,
    ORDER_SET = 2,
}

// Python's OrderSettings.ALL_SETTINGS was primarily for runtime validation.
// In TypeScript, the enum itself serves as the definition of possible values.
// If specific runtime checks against a set of these values are needed elsewhere,
// it can be reconstructed there, e.g., new Set(Object.values(OrderSettings).filter(v => typeof v === 'number'))
// For now, ALL_SETTINGS is omitted as it's not directly translatable or idiomatic in the same way for enums.
