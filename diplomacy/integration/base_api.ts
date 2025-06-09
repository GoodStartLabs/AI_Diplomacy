// diplomacy/integration/base_api.ts

import { DiplomacyGame } from '../engine/game'; // Adjust path as necessary
// Consider defining more specific interfaces if DiplomacyGame is too broad or for return types.

/**
 * Interface for the data returned by get_game_and_power.
 */
export interface GameAndPower {
    game: DiplomacyGame | null;
    powerName: string | null;
    // Potentially add other relevant details like game ID, phase, deadlines, etc.
    // gameId?: string | number;
    // currentPhase?: string;
    // deadline?: Date;
}

/**
 * Base class for Diplomacy game APIs.
 * Defines a common interface for interacting with different Diplomacy platforms.
 */
export abstract class BaseDiplomacyAPI {
    protected apiKey: string;
    protected connectTimeout: number;
    protected requestTimeout: number;

    /**
     * Constructor for BaseDiplomacyAPI.
     * @param apiKey - The API key to use for sending API requests.
     * @param connectTimeout - Max time (ms) to wait for connection. Defaults to 30000ms.
     * @param requestTimeout - Max time (ms) to wait for request processing. Defaults to 60000ms.
     */
    constructor(apiKey: string, connectTimeout: number = 30000, requestTimeout: number = 60000) {
        this.apiKey = apiKey;
        this.connectTimeout = connectTimeout;
        this.requestTimeout = requestTimeout;
        // Specific HTTP client initialization will be handled by concrete implementations.
    }

    /**
     * Retrieves the game state and the power the client is playing.
     * Arguments are specific to each implementation.
     * @param args - Implementation-specific arguments.
     * @returns A Promise resolving to a GameAndPower object or null if an error occurred.
     */
    abstract get_game_and_power(...args: any[]): Promise<GameAndPower | null>;

    /**
     * Submits orders to the server.
     * @param game - A DiplomacyGame object representing the current state of the game.
     * @param powerName - The name of the power submitting the orders (e.g., 'FRANCE').
     * @param orders - An array of strings representing the orders (e.g., ['A PAR H', 'F BRE - MAO']).
     * @param wait - Optional. If true, indicates the player is not ready (sets ready=false).
     *               If false, indicates player is ready (sets ready=true).
     *               If undefined, the platform's default behavior for submitting orders is used.
     * @returns A Promise resolving to true for success, false for failure.
     */
    abstract set_orders(game: DiplomacyGame, powerName: string, orders: string[], wait?: boolean): Promise<boolean>;

    // Other potential abstract methods for a comprehensive API client:
    // abstract get_game_history(gameId: string | number): Promise<GameHistory | null>;
    // abstract send_message(gameId: string | number, recipient: string, message: string): Promise<boolean>;
    // abstract get_deadlines(gameId: string | number): Promise<Date[] | null>;
    // abstract get_games_list(): Promise<Array<{gameId: string | number, name: string, phase: string}> | null>;
}
