// diplomacy/server/server_game.ts

import { DiplomacyGame, DiplomacyGameOptions } from '../../engine/game';
import { Message, GLOBAL, OBSERVER, OMNISCIENT, SYSTEM } from '../../engine/message';
import { Power } from '../../engine/power'; // Assuming PowerTs is exported as Power
import {
    MODERATOR_USERNAMES, OBSERVER as OBSERVER_STRING_KEY, OMNISCIENT as OMNISCIENT_STRING_KEY,
    OMNISCIENT_USERNAMES, OBSERVER_TYPE, OMNISCIENT_TYPE, MASTER_TYPE, FORMING, NEUTRAL
} from '../utils/strings'; // Adjust path as necessary
import {
    update_model, DefaultValueType, SequenceType, OptionalValueType, JsonableClassType, ParserType
} from '../utils/parsing'; // Adjust path as necessary
import { GamePhaseData } from '../utils/game_phase_data'; // Adjust path as necessary
import { DiplomacyException, ResponseException } from '../utils/exceptions'; // Adjust path as necessary
import { JsonableModel } from '../utils/jsonable';

// Placeholder for the main Server type/interface, to avoid circular dependencies if Server imports ServerGame
export interface DiplomacyServerInterface {
    users: { has_admin: (username: string) => boolean }; // Simplified Users interface for now
    get_daide_port: (game_id: string) => number | null;
    // Add other methods/properties of Server that ServerGame might interact with
}

export interface ServerGameOptions extends DiplomacyGameOptions {
    server?: DiplomacyServerInterface;
    [MODERATOR_USERNAMES]?: Set<string>;
    [OBSERVER_STRING_KEY]?: Power;
    [OMNISCIENT_STRING_KEY]?: Power;
    [OMNISCIENT_USERNAMES]?: Set<string>;
}


export class ServerGame extends DiplomacyGame {
    public server?: DiplomacyServerInterface;
    public omniscient_usernames: Set<string>;
    public moderator_usernames: Set<string>;
    public observer: Power;
    public omniscient: Power;

    public static override model: JsonableModel = update_model(DiplomacyGame.model, {
        [MODERATOR_USERNAMES]: new DefaultValueType(new SequenceType(ParserType.STR, () => new Set<string>()), () => new Set()),
        [OBSERVER_STRING_KEY]: new OptionalValueType(new JsonableClassType(Power)),
        [OMNISCIENT_STRING_KEY]: new OptionalValueType(new JsonableClassType(Power)),
        [OMNISCIENT_USERNAMES]: new DefaultValueType(new SequenceType(ParserType.STR, () => new Set<string>()), () => new Set()),
    });

    constructor(options: ServerGameOptions = {}) {
        super(options); // Call base Game constructor
        this.server = options.server;
        this.omniscient_usernames = options[OMNISCIENT_USERNAMES] || new Set<string>();
        this.moderator_usernames = options[MODERATOR_USERNAMES] || new Set<string>();

        // Initialize special powers.
        // The Power constructor in engine/power.ts needs to accept (game: DiplomacyGame, name: string)
        this.observer = options[OBSERVER_STRING_KEY] || new Power(this, OBSERVER_TYPE);
        this.omniscient = options[OMNISCIENT_STRING_KEY] || new Power(this, OMNISCIENT_TYPE);

        // Ensure these powers are marked as controlled by the system/observer type
        // The set_controlled method in Power class needs to handle string arguments like OBSERVER_TYPE
        this.observer.set_controlled(OBSERVER_TYPE);
        this.omniscient.set_controlled(OMNISCIENT_TYPE); // Or perhaps OMNISCIENT_TYPE
    }

    public is_server_game(): boolean {
        return true; // This class is ServerGame
    }

    public get_related_power_names(power_name: string): string[] {
        if (this.powers[power_name]) {
            const related_power = this.powers[power_name];
            if (related_power.is_controlled()) { // is_controlled needs to be a method in Power
                return this.get_controlled_power_names(related_power.get_controller()!); // get_controller might return string | null
            }
            return [power_name];
        }
        return [];
    }

    public filter_phase_data(phase_data: GamePhaseData, role: string, is_current: boolean): GamePhaseData {
        if (role === OMNISCIENT_TYPE) {
            return phase_data;
        }
        if (role === OBSERVER_TYPE) {
            return new GamePhaseData({
                name: phase_data.name,
                state: phase_data.state,
                orders: phase_data.orders, // Observers see all orders in past phases
                results: phase_data.results,
                messages: this.filter_messages(phase_data.messages, role)
            });
        }

        // Filter for power roles
        const related_power_names = this.get_related_power_names(role);
        const messages = this.filter_messages(phase_data.messages, related_power_names);
        let orders = phase_data.orders;
        if (is_current) {
            orders = {};
            for (const power_name of related_power_names) {
                if (phase_data.orders && phase_data.orders[power_name]) {
                    orders[power_name] = phase_data.orders[power_name];
                }
            }
        }
        return new GamePhaseData({
            name: phase_data.name,
            state: phase_data.state,
            orders: orders,
            messages: messages,
            results: phase_data.results
        });
    }

    public game_can_start(): boolean {
        return this.is_game_forming && !this.start_master && this.has_expected_controls_count();
    }

    public get_messages(game_role: string, timestamp_from?: number, timestamp_to?: number): Message[] {
        return this.filter_messages(super.get_messages(), game_role, timestamp_from, timestamp_to); // super.get_messages() gets all current messages
    }

    public get_message_history(game_role: string): Record<string, Message[]> {
        const filtered_history: Record<string, Message[]> = {};
        for (const short_phase in this.message_history) {
            filtered_history[short_phase] = this.filter_messages(this.message_history[short_phase], game_role);
        }
        return filtered_history;
    }

    public get_user_power_names(username: string): string[] {
        return Object.values(this.powers)
            .filter(power => power.is_controlled_by(username))
            .map(power => power.name);
    }

    public new_system_message(recipient: string, body: string): Message {
        if (!(recipient === GLOBAL || recipient === OBSERVER || recipient === OMNISCIENT || this.powers[recipient])) {
            throw new DiplomacyException(`Invalid recipient for system message: ${recipient}`);
        }
        const message = new Message({
            phase: this.current_short_phase,
            sender: SYSTEM,
            recipient: recipient,
            message: body,
            // timestamp will be set by add_message
        });
        this.add_message(message);
        return message;
    }

    // TODO: Implement as_power_game, as_omniscient_game, as_observer_game, cast
    // These require careful handling of game state copying and filtering.
    // For now, placeholder:
    public cast(role: string, for_username: string): DiplomacyGame {
        console.warn("ServerGame.cast() is a simplified placeholder.");
         // This should create a new Game instance, then filter its properties.
        const game_dict = this.to_dict(); // Uses Jsonable.to_dict
        const new_game_options: DiplomacyGameOptions = {
            ...game_dict,
            // message_history and messages will be filtered below
        };
        const game = new DiplomacyGame(new_game_options); // Create a new game instance
        game.error = []; // Clear errors

        if (role === OBSERVER_TYPE) {
            game.message_history = this.get_message_history(OBSERVER_TYPE);
            game.messages = this.get_messages(OBSERVER_TYPE);
            Object.values(game.powers).forEach(p => { p.vote = NEUTRAL; p.clear_orders(); });
        } else if (role === OMNISCIENT_TYPE) {
            game.message_history = this.get_message_history(OMNISCIENT_TYPE);
            game.messages = this.get_messages(OMNISCIENT_TYPE);
        } else if (this.powers[role]) { // Power role
            game.message_history = this.get_message_history(role);
            game.messages = this.get_messages(role);
            const related_power_names = this.get_related_power_names(role);
            Object.values(game.powers).forEach(p => {
                if (!related_power_names.includes(p.name)) {
                    p.vote = NEUTRAL;
                    p.clear_orders();
                }
            });
        }

        game.role = role;
        // game.controlled_powers = this.get_controlled_power_names(for_username); // Needs get_controlled_power_names
        game.observer_level = this.get_observer_level(for_username);
        game.daide_port = this.server?.get_daide_port(this.game_id) ?? null;
        return game;
    }


    public is_controlled_by(power_name: string, username: string): boolean {
        const power = this.powers[power_name];
        return power ? power.is_controlled_by(username) : false;
    }

    public get_observer_level(username: string): string | null {
        if ((this.server && this.server.users.has_admin(username)) || this.is_moderator(username)) {
            return MASTER_TYPE;
        }
        if (this.is_omniscient(username)) {
            return OMNISCIENT_TYPE;
        }
        if (!this.properties.no_observations) { // Assuming no_observations is a property from base Game
            return OBSERVER_TYPE;
        }
        return null;
    }

    public *get_reception_addresses(): Generator<[string, string]> {
        for (const power of Object.values(this.powers)) {
            for (const token of power.tokens) yield [power.name, token];
        }
        for (const token of this.observer.tokens) yield [this.observer.name, token];
        for (const token of this.omniscient.tokens) yield [this.omniscient.name, token];
    }

    // ... other token and permission methods ... (has_token, add_omniscient_token, etc.)
    // These will largely be translations of Python set/dict operations to TS Map/Set.

    public has_token(token: string): boolean {
        if (this.omniscient.has_token(token)) return true;
        if (this.observer.has_token(token)) return true;
        for (const power of Object.values(this.powers)) {
            if (power.has_token(token)) return true;
        }
        return false;
    }

    public add_omniscient_token(token: string): void {
        if (this.observer.has_token(token)) throw new ResponseException('Token already registered as observer.');
        if (this.has_player_token(token)) throw new ResponseException('Token already registered as player.');
        this.omniscient.add_token(token);
    }

    public add_observer_token(token: string): void {
        if (this.omniscient.has_token(token)) throw new ResponseException('Token already registered as omniscient.');
        if (this.has_player_token(token)) throw new ResponseException('Token already registered as player.');
        this.observer.add_token(token);
    }

    public control(power_name: string, username: string, token: string): void {
        if (this.observer.has_token(token)) throw new ResponseException('Token already registered as observer.');
        if (this.omniscient.has_token(token)) throw new ResponseException('Token already registered as omniscient.');

        const power = this.powers[power_name];
        if (!power) throw new DiplomacyException(`Power ${power_name} not found in game ${this.game_id}`);

        if (power.is_controlled() && !power.is_controlled_by(username)) {
            throw new ResponseException('Power already controlled by another user.');
        }
        power.set_controlled(username);
        power.add_token(token);
    }

    public is_moderator(username: string): boolean {
        return this.moderator_usernames.has(username);
    }

    public is_omniscient(username: string): boolean {
        return this.omniscient_usernames.has(username);
    }

    public promote_moderator(username: string): void {
        this.moderator_usernames.add(username);
    }

    public promote_omniscient(username: string): void {
        this.omniscient_usernames.add(username);
    }

    // Stubs for remaining methods that require more complex logic or dependencies
    public has_player_token(token: string): boolean { /* ... */ return false; }
    public remove_observer_token(token: string): void { this.observer.remove_tokens([token]); }
    public remove_omniscient_token(token: string): void { this.omniscient.remove_tokens([token]); }
    public remove_token(token: string): void { /* ... */ }


    public override process(): { prev_phase_data: GamePhaseData | null, current_phase_data: GamePhaseData | null, kicked_powers: Record<string, Set<string>> | null } {
        if (!this.is_active) { // Assuming is_active getter from base Game
            return { prev_phase_data: null, current_phase_data: null, kicked_powers: null };
        }

        const kicked_powers: Record<string, Set<string>> = {};
        const orderable_locations_all_powers = this.get_orderable_locations_all_powers(); // from base Game

        if (!this.properties.civil_disorder_nodes) { // civil_disorder_nodes is a Rule
            Object.values(this.powers).forEach(power => {
                if (power.is_controlled() &&
                    !power.is_order_set() && // power.order_is_set needs to be implemented in Power.ts
                    orderable_locations_all_powers[power.name] &&
                    orderable_locations_all_powers[power.name].length > 0) {

                    kicked_powers[power.name] = new Set(power.tokens);
                    power.set_controlled(null); // Becomes AI/dummy
                    power.clear_tokens();
                }
            });
        }

        if (Object.keys(kicked_powers).length > 0) {
            this.set_status(FORMING); // Assuming set_status is available from base Game
            return { prev_phase_data: null, current_phase_data: null, kicked_powers };
        }

        const previous_phase_data = super.process(); // Call base Game process

        if (this.count_controlled_powers() < (this.properties.expected_controls_count || Object.keys(this.powers).length)) {
             // Compare with a reasonable default if expected_controls_count is not set
            this.set_status(FORMING);
        }

        const current_phase_data = this.get_phase_data(this.current_short_phase); // from base Game
        return { prev_phase_data, current_phase_data, kicked_powers: null };
    }
}
