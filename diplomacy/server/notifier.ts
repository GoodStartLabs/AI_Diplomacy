// diplomacy/server/notifier.ts

import { ServerGame, DiplomacyServerInterface } from './server_game'; // DiplomacyServerInterface needs Users and a notifications queue
import { Power } from '../../engine/power';
import * as notifications from '../../communication/notifications'; // Assuming this is the path to translated notifications
import { GAME, OBSERVER_TYPE, OMNISCIENT_TYPE } from '../utils/strings';
import { GamePhaseData } from '../utils/game_phase_data';
import { Users } from './users'; // Needed for server.users type

// Placeholder for ConnectionHandler if not fully defined elsewhere
// This is a simplified interface based on Notifier's usage.
export interface ConnectionHandler {
    translate_notification(notification: notifications.AbstractNotification): any[] | null; // Return type might be more specific
    // send(data: any): void; // Actual sending mechanism might be part of connection_handler or server.notifications.put
}

export class Notifier {
    private server: DiplomacyServerInterface; // Should have 'users' and 'notifications' queue
    private ignore_tokens: Set<string> | null = null;
    private ignore_addresses: Map<string, Set<string>> | null = null; // powerName -> Set<token>

    constructor(server: DiplomacyServerInterface, ignore_tokens?: string[] | null, ignore_addresses?: Array<[string, string]> | null) {
        this.server = server;

        if (ignore_tokens && ignore_addresses) {
            throw new Error('Notifier cannot ignore both tokens and addresses.');
        }

        if (ignore_tokens) {
            this.ignore_tokens = new Set(ignore_tokens);
        } else if (ignore_addresses) {
            this.ignore_addresses = new Map<string, Set<string>>();
            for (const [power_name, token] of ignore_addresses) {
                if (!this.ignore_addresses.has(power_name)) {
                    this.ignore_addresses.set(power_name, new Set<string>());
                }
                this.ignore_addresses.get(power_name)!.add(token);
            }
        }
    }

    private ignores(notification: notifications.AbstractNotification | notifications.GameNotification): boolean {
        if (this.ignore_tokens) {
            return this.ignore_tokens.has(notification.token);
        }
        if (this.ignore_addresses && notification.level === GAME) {
            // GameNotification has game_role
            const gameNotif = notification as notifications.GameNotification;
            if (gameNotif.game_role && this.ignore_addresses.has(gameNotif.game_role)) {
                return this.ignore_addresses.get(gameNotif.game_role)!.has(notification.token);
            }
        }
        return false;
    }

    private async _notify(notification: notifications.AbstractNotification): Promise<void> {
        // Assume this.server.users is an instance of the Users class previously defined
        const connection_handler = (this.server.users as Users).get_connection_handler(notification.token);

        if (!this.ignores(notification) && connection_handler) {
            const translated_notifications = (connection_handler as ConnectionHandler).translate_notification(notification);
            if (translated_notifications) {
                for (const translated_notification of translated_notifications) {
                    // Assuming server.notifications.put is async or can be awaited if it returns a Promise
                    await (this.server.notifications as any).put([connection_handler, translated_notification]);
                }
            }
        }
    }

    private async _notify_game(server_game: ServerGame, notification_class: notifications.GameNotificationConstructor, options: Record<string, any> = {}): Promise<void> {
        for (const [game_role, token] of server_game.get_reception_addresses()) {
            await this._notify(new notification_class({
                token,
                game_id: server_game.game_id,
                game_role,
                ...options,
            }));
        }
    }

    private async _notify_power(game_id: string, power: Power, notification_class: notifications.GameNotificationConstructor, options: Record<string, any> = {}): Promise<void> {
        for (const token of power.tokens) {
            await this._notify(new notification_class({
                token,
                game_id,
                game_role: power.name,
                ...options,
            }));
        }
    }

    public async notify_game_processed(server_game: ServerGame, previous_phase_data: GamePhaseData, current_phase_data: GamePhaseData): Promise<void> {
        // Notify observers and omniscient observers
        for (const [game_role, token] of server_game.get_observer_addresses()) { // Simple observers
            await this._notify(new notifications.GameProcessed({
                token,
                game_id: server_game.game_id,
                game_role,
                previous_phase_data: server_game.filter_phase_data(previous_phase_data, OBSERVER_TYPE, false),
                current_phase_data: server_game.filter_phase_data(current_phase_data, OBSERVER_TYPE, true),
            }));
        }
        for (const [game_role, token] of server_game.get_omniscient_addresses()) {
            await this._notify(new notifications.GameProcessed({
                token,
                game_id: server_game.game_id,
                game_role, // should be OMNISCIENT_TYPE effectively
                previous_phase_data: server_game.filter_phase_data(previous_phase_data, OMNISCIENT_TYPE, false),
                current_phase_data: server_game.filter_phase_data(current_phase_data, OMNISCIENT_TYPE, true),
            }));
        }
        // Notify powers
        for (const power of Object.values(server_game.powers)) {
            await this._notify_power(server_game.game_id, power, notifications.GameProcessed, {
                previous_phase_data: server_game.filter_phase_data(previous_phase_data, power.name, false),
                current_phase_data: server_game.filter_phase_data(current_phase_data, power.name, true),
            });
        }
        // Notify wait flags
        for (const power of Object.values(server_game.powers)) {
            await this.notify_power_wait_flag(server_game, power, power.wait);
        }
    }

    public async notify_account_deleted(username: string): Promise<void> {
        const userTokens = (this.server.users as Users).get_tokens(username);
        for (const token_to_notify of userTokens) {
            await this._notify(new notifications.AccountDeleted({ token: token_to_notify }));
        }
    }

    public async notify_game_deleted(server_game: ServerGame): Promise<void> {
        await this._notify_game(server_game, notifications.GameDeleted);
    }

    public async notify_game_powers_controllers(server_game: ServerGame): Promise<void> {
        await this._notify_game(server_game, notifications.PowersControllers, {
            powers: server_game.get_controllers(), // Assuming get_controllers exists on ServerGame
            timestamps: server_game.get_controllers_timestamps(), // Assuming this exists
        });
    }

    public async notify_game_status(server_game: ServerGame): Promise<void> {
        await this._notify_game(server_game, notifications.GameStatusUpdate, { status: server_game.status });
    }

    public async notify_game_phase_data(server_game: ServerGame): Promise<void> {
        const phase_data = server_game.get_phase_data(server_game.current_short_phase); // get current phase data
        const state_type = GAME; // In Python, this was strings.STATE, assuming GAME is the equivalent level

        // Notify omniscient
        await this.notify_game_addresses(server_game.game_id, Array.from(server_game.get_omniscient_addresses()), notifications.GamePhaseUpdate, {
            phase_data: server_game.filter_phase_data(phase_data, OMNISCIENT_TYPE, true),
            phase_data_type: state_type,
        });
        // Notify observers
        await this.notify_game_addresses(server_game.game_id, Array.from(server_game.get_observer_addresses()), notifications.GamePhaseUpdate, {
            phase_data: server_game.filter_phase_data(phase_data, OBSERVER_TYPE, true),
            phase_data_type: state_type,
        });
        // Notify powers
        for (const power_name of server_game.get_map_power_names()) {
             await this.notify_game_addresses(server_game.game_id, Array.from(server_game.get_power_addresses(power_name)), notifications.GamePhaseUpdate, {
                phase_data: server_game.filter_phase_data(phase_data, power_name, true),
                phase_data_type: state_type,
            });
        }
    }

    public async notify_game_vote_updated(server_game: ServerGame): Promise<void> {
        // Notify observers
        for (const [game_role, token] of server_game.get_observer_addresses()) {
            await this._notify(new notifications.VoteCountUpdated({
                token, game_id: server_game.game_id, game_role,
                count_voted: server_game.count_voted(),
                count_expected: server_game.count_controlled_powers()
            }));
        }
        // Notify omniscient
        for (const [game_role, token] of server_game.get_omniscient_addresses()) {
             await this._notify(new notifications.VoteUpdated({
                token, game_id: server_game.game_id, game_role,
                vote: Object.fromEntries(Object.values(server_game.powers).map(p => [p.name, p.vote]))
            }));
        }
        // Notify each power
        for (const power of Object.values(server_game.powers)) {
            await this._notify_power(server_game.game_id, power, notifications.PowerVoteUpdated, {
                count_voted: server_game.count_voted(),
                count_expected: server_game.count_controlled_powers(),
                vote: power.vote
            });
        }
    }

    public async notify_power_orders_update(server_game: ServerGame, power: Power, orders: string[]): Promise<void> {
        await this._notify_power(server_game.game_id, power, notifications.PowerOrdersUpdate, {
            power_name: power.name, orders
        });
        const observer_addresses = [
            ...Array.from(server_game.get_omniscient_addresses()),
            ...Array.from(server_game.get_observer_addresses())
        ];
        await this.notify_game_addresses(server_game.game_id, observer_addresses, notifications.PowerOrdersUpdate, {
             power_name: power.name, orders
        });

        const other_powers_addresses: Array<[string, string]> = [];
        Object.keys(server_game.powers).forEach(other_power_name => {
            if (other_power_name !== power.name) {
                other_powers_addresses.push(...Array.from(server_game.get_power_addresses(other_power_name)));
            }
        });
        await this.notify_game_addresses(server_game.game_id, other_powers_addresses, notifications.PowerOrdersFlag, {
            power_name: power.name, order_is_set: power.is_order_set() // Assuming is_order_set exists
        });
    }

    public async notify_power_wait_flag(server_game: ServerGame, power: Power, wait_flag: boolean): Promise<void> {
        await this._notify_game(server_game, notifications.PowerWaitFlag, { power_name: power.name, wait: wait_flag });
    }

    public async notify_cleared_orders(server_game: ServerGame, power_name: string | null): Promise<void> {
        await this._notify_game(server_game, notifications.ClearedOrders, { power_name });
    }

    public async notify_cleared_units(server_game: ServerGame, power_name: string | null): Promise<void> {
        await this._notify_game(server_game, notifications.ClearedUnits, { power_name });
    }

    public async notify_cleared_centers(server_game: ServerGame, power_name: string | null): Promise<void> {
        await this._notify_game(server_game, notifications.ClearedCenters, { power_name });
    }

    public async notify_game_message(server_game: ServerGame, game_message: Message): Promise<void> {
        if (game_message.is_global()) { // Assuming is_global method on Message
            await this._notify_game(server_game, notifications.GameMessageReceived, { message: game_message });
        } else {
            const power_from = server_game.powers[game_message.sender];
            const power_to = server_game.powers[game_message.recipient];
            if (power_from) {
                await this._notify_power(server_game.game_id, power_from, notifications.GameMessageReceived, { message: game_message });
            }
            if (power_to && power_to !== power_from) { // Avoid double sending if sender is also recipient (though unlikely for P2P)
                await this._notify_power(server_game.game_id, power_to, notifications.GameMessageReceived, { message: game_message });
            }
            for (const [game_role, token] of server_game.get_omniscient_addresses()) {
                await this._notify(new notifications.GameMessageReceived({
                    token, game_id: server_game.game_id, game_role, message: game_message
                }));
            }
        }
    }

    public async notify_game_addresses(game_id: string, addresses: Array<[string, string]>, notification_class: notifications.GameNotificationConstructor, options: Record<string, any> = {}): Promise<void> {
        for (const [game_role, token] of addresses) {
            await this._notify(new notification_class({
                token,
                game_id,
                game_role,
                ...options
            }));
        }
    }
}
