// diplomacy/integration/webdiplomacy_net/api.ts

import fetch, { Headers, RequestInit, Response } from 'node-fetch';
import { URLSearchParams } from 'url';
import { Cookie, CookieJar } from 'tough-cookie';
import { DiplomacyGame } from '../../../engine/game'; // Adjust path as necessary
import { BaseDiplomacyAPI, GameAndPower } from '../base_api';
import { state_dict_to_game_and_power } from './game'; // To be created
import { WebDiplomacyOrder } from './orders'; // To be created (renamed from Order to avoid conflict)
import { CACHE, GameIdCountryId, getMapData } from './utils';

const API_USER_AGENT = 'DiplomacyTS Client v0.1'; // Update as appropriate
const API_WEBDIPLOMACY_NET = process.env.API_WEBDIPLOMACY || 'https://webdiplomacy.net/api.php';

// Custom Error for API specific issues
export class WebDiplomacyAPIError extends Error {
    constructor(message: string, public response?: Response, public data?: any) {
        super(message);
        this.name = 'WebDiplomacyAPIError';
    }
}

export class API extends BaseDiplomacyAPI {
    private cookieJar: CookieJar;

    constructor(apiKey: string, connectTimeout: number = 30000, requestTimeout: number = 60000) {
        super(apiKey, connectTimeout, requestTimeout);
        this.cookieJar = new CookieJar();
        // Note: connectTimeout and requestTimeout are not directly supported by node-fetch in the same way as Tornado.
        // fetch uses AbortController for timeouts. This can be added to _sendRequest if needed.
    }

    private async _sendRequest(url: string, method: 'GET' | 'POST', body?: any): Promise<Response> {
        const headers = new Headers({
            'Authorization': `Bearer ${this.apiKey}`,
            'User-Agent': API_USER_AGENT,
        });

        if (method === 'POST' && body) {
            headers.set('Content-Type', 'application/json'); // Assuming JSON body for POST
        }

        // Add cookies to request
        const cookieString = await this.cookieJar.getCookieString(url);
        if (cookieString) {
            headers.set('Cookie', cookieString);
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);

        let response: Response;
        try {
            const options: RequestInit = {
                method,
                headers,
                signal: controller.signal,
            };
            if (method === 'POST' && body) {
                options.body = typeof body === 'string' ? body : JSON.stringify(body);
            }
            response = await fetch(url, options);
        } catch (error: any) {
            clearTimeout(timeoutId);
            // Differentiate network errors from AbortError for timeouts
            if (error.name === 'AbortError') {
                throw new WebDiplomacyAPIError(`Request timed out after ${this.requestTimeout}ms: ${method} ${url}`, undefined, error);
            }
            throw new WebDiplomacyAPIError(`Network error during request: ${method} ${url}: ${error.message}`, undefined, error);
        } finally {
            clearTimeout(timeoutId);
        }

        // Store cookies from response
        const setCookieHeader = response.headers.raw()['set-cookie'];
        if (setCookieHeader) {
            await Promise.all(setCookieHeader.map(cookie => this.cookieJar.setCookie(Cookie.parse(cookie)!, response.url)));
        }

        return response;
    }

    private async _sendGetRequest(url: string): Promise<Response> {
        return this._sendRequest(url, 'GET');
    }

    private async _sendPostRequest(url: string, body: any): Promise<Response> {
        return this._sendRequest(url, 'POST', body);
    }

    async list_games_with_players_in_cd(): Promise<GameIdCountryId[]> {
        const route = 'players/cd';
        const params = new URLSearchParams({ route });
        const url = `${API_WEBDIPLOMACY_NET}?${params.toString()}`;
        const return_val: GameIdCountryId[] = [];

        try {
            const response = await this._sendGetRequest(url);
            if (response.ok) {
                const list_games_players = await response.json() as Array<{gameID: number, countryID: number}>;
                list_games_players.forEach(game_player => {
                    return_val.push({ game_id: game_player.gameID, country_id: game_player.countryID });
                });
            } else {
                const errorBody = await response.text();
                console.warn(`API._list_games_with_players_in_cd: Error during "${route}". Status: ${response.status}. Body: ${errorBody}`);
                throw new WebDiplomacyAPIError(`Failed to list CD games`, response, errorBody);
            }
        } catch (error: any) {
            console.error(`API._list_games_with_players_in_cd: Unable to connect or parse. Error: ${error.message}`);
            if (!(error instanceof WebDiplomacyAPIError)) {
                 throw new WebDiplomacyAPIError(`Failed to list CD games: ${error.message}`, undefined, error);
            }
            throw error;
        }
        return return_val;
    }

    async list_games_with_missing_orders(): Promise<GameIdCountryId[]> {
        const route = 'players/missing_orders';
        const params = new URLSearchParams({ route });
        const url = `${API_WEBDIPLOMACY_NET}?${params.toString()}`;
        const return_val: GameIdCountryId[] = [];

        try {
            const response = await this._sendGetRequest(url);
            if (response.ok) {
                const list_games_players = await response.json() as Array<{gameID: number, countryID: number}>;
                list_games_players.forEach(game_player => {
                    return_val.push({ game_id: game_player.gameID, country_id: game_player.countryID });
                });
            } else {
                const errorBody = await response.text();
                console.warn(`API.list_games_with_missing_orders: Error during "${route}". Status: ${response.status}. Body: ${errorBody}`);
                throw new WebDiplomacyAPIError(`Failed to list missing orders games`, response, errorBody);
            }
        } catch (error: any) {
            console.error(`API.list_games_with_missing_orders: Unable to connect or parse. Error: ${error.message}`);
             if (!(error instanceof WebDiplomacyAPIError)) {
                 throw new WebDiplomacyAPIError(`Failed to list missing orders games: ${error.message}`, undefined, error);
            }
            throw error;
        }
        return return_val;
    }

    async get_game_and_power(game_id: number, country_id: number, max_phases?: number): Promise<GameAndPower | null> {
        const route = 'game/status';
        const params = new URLSearchParams({
            route,
            gameID: game_id.toString(),
            countryID: country_id.toString()
        });
        const url = `${API_WEBDIPLOMACY_NET}?${params.toString()}`;

        try {
            const response = await this._sendGetRequest(url);
            if (response.ok) {
                const state_dict = await response.json();
                // state_dict_to_game_and_power will be implemented in game.ts
                // It needs to create a DiplomacyGame instance.
                return state_dict_to_game_and_power(state_dict, country_id, max_phases);
            } else {
                const errorBody = await response.text();
                console.warn(`API.get_game_and_power: Error during "${route}". Status: ${response.status}. Body: ${errorBody}`);
                throw new WebDiplomacyAPIError(`Failed to get game and power for gameID ${game_id}`, response, errorBody);
            }
        } catch (error: any) {
            console.error(`API.get_game_and_power: Unable to connect or parse for gameID ${game_id}. Error: ${error.message}`);
             if (!(error instanceof WebDiplomacyAPIError)) {
                throw new WebDiplomacyAPIError(`Failed to get game and power: ${error.message}`, undefined, error);
            }
            throw error;
        }
        return null; // Should be unreachable if errors throw
    }

    async set_orders(game: DiplomacyGame, power_name: string, orders: string[], wait?: boolean): Promise<boolean> {
        console.info(`[${game.game_id}/${game.get_current_phase()}/${power_name}] - Submitting orders: ${orders.join(', ')}`);

        const mapData = getMapData(game.map_name || 'standard');
        if (!mapData || !mapData.power_to_ix) {
            console.error(`set_orders: Map data or power_to_ix not found for map ${game.map_name}`);
            return false;
        }

        const countryID = mapData.power_to_ix[power_name.toUpperCase()];
        if (countryID === undefined) {
            console.error(`set_orders: Country ID not found for power ${power_name} in map ${game.map_name}`);
            return false;
        }

        // Convert orders using WebDiplomacyOrder class (to be created in orders.ts)
        const orders_dict = orders.map(orderStr =>
            new WebDiplomacyOrder(orderStr, game.map_name, game.phase_type, game).to_dict()
        );

        const current_phase = game.get_current_phase();
        let turn = -1;
        let phase_for_api = 'Diplomacy';

        if (current_phase !== 'COMPLETED' && current_phase.length >=6 /* e.g. S1901M */) {
            const season = current_phase[0];
            const current_year = parseInt(current_phase.substring(1, 5), 10);
            const phase_type_char = current_phase[5];
            const nb_years = current_year - (game.map.first_year || 1901) ; // game.map should be populated
            turn = 2 * nb_years + (season.toUpperCase() === 'S' ? 0 : 1);
            phase_for_api = {'M': 'Diplomacy', 'R': 'Retreats', 'A': 'Builds'}[phase_type_char.toUpperCase()] || 'Diplomacy';
        }

        const route = 'game/orders';
        const url = `${API_WEBDIPLOMACY_NET}?route=${route}`; // No need for URLSearchParams for route here
        const body: Record<string, any> = {
            gameID: parseInt(game.game_id, 10), // Ensure game_id is number
            turn,
            phase: phase_for_api,
            countryID,
            orders: orders_dict.filter(o => o), // Filter out any null/undefined from to_dict if order was invalid
        };

        if (wait !== undefined) {
            body['ready'] = !wait ? 'Yes' : 'No'; // wait=true means ready=No
        }

        try {
            const response = await this._sendPostRequest(url, body); // Body will be stringified by _sendRequest
            if (!response.ok) {
                const errorBody = await response.text();
                console.warn(`API.set_orders: Error during "${route}". Status: ${response.status}. Body: ${errorBody}`);
                return false;
            }

            if (!orders || orders.length === 0) { // If only setting ready flag
                return true;
            }

            const response_body_text = await response.text();
            if (!response_body_text) {
                console.warn(`API.set_orders: Warning during "${route}". No response body received.`);
                return false; // Or true depending on desired strictness - Python returns False here
            }

            const received_orders_payload = JSON.parse(response_body_text);
            // TODO: Validate received orders against submitted orders as in Python version
            // This requires parsing received_orders_payload which is an array of order strings.
            // For now, assume success if response was ok and body was received.
            console.log(`API.set_orders: Orders submitted, received payload:`, received_orders_payload);
            return true;

        } catch (error: any) {
            console.error(`API.set_orders: Unable to connect or process for gameID ${game.game_id}. Error: ${error.message}`);
            return false;
        }
    }
}
