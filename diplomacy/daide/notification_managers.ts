// diplomacy/daide/notification_managers.ts

import {
    SCO_NOTIFICATION as SupplyCenterNotificationTs, // Aliases from daide/notifications
    NOW_NOTIFICATION as CurrentPositionNotificationTs,
    TME_NOTIFICATION as TimeToDeadlineNotificationTs,
    DRW_NOTIFICATION as DrawNotificationTs,
    SLO_NOTIFICATION as SoloNotificationTs,
    SMR_NOTIFICATION as SummaryNotificationTs,
    OFF_NOTIFICATION as TurnOffNotificationTs,
    ORD_NOTIFICATION as OrderResultNotificationTs,
    HLO_NOTIFICATION as HelloNotificationTs,
    FRM_NOTIFICATION as MessageFromNotificationTs,
    DaideNotification
} from './notifications';
import { parse_order_to_bytes_ts, get_user_connection, ClientConnectionInfo } from './utils';
import { DEFAULT_LEVEL } from './index'; // from diplomacy/daide/__init__.py
import * as daideTokens from './tokens'; // For specific tokens like SUC, NSO if needed directly

// Placeholders for server-internal and engine types
interface MasterServer {
    users: any; // Placeholder for server.users (e.g., UserManagementClass)
    get_game(gameId: string): DiplomacyGame | null;
}
interface DiplomacyGame {
    game_id: string;
    get_current_phase(): string;
    powers: Record<string, EnginePower>;
    map_name: string;
    map: any; // Placeholder for map object for find_next_phase, phase_abbr, phase_long
    deadline: number;
    rules: string[];
    status: string; // e.g., 'ACTIVE', 'COMPLETED'
    has_draw_vote(): boolean;
    state_history: any; // Placeholder for state history object with last_value() and items()
}
interface EnginePower {
    name: string;
    orders: Record<string, string>; // unit_str -> order_str
    units: string[];
    centers: string[];
    retreats: Record<string, string[]>; // unit_str -> possible_retreat_provinces[]
    get_controller(): string | null; // Username or null
    // adjust: any[]; // If used by OrderSplitter logic
}
interface DaideUser { // From daide/utils placeholder
    username: string;
    passcode: number;
    client_name: string;
    client_version: string;
}
interface ConnectionHandlerTs { // From daide/connection_handler
    token: string | null;
    // other properties
}

// Placeholders for internal notifications from diplomacy.communication.notifications
interface InternalBaseNotification { __type__: string; game_id: string; }
interface InternalGameProcessedNotification extends InternalBaseNotification {
    __type__: "GameProcessed";
    previous_phase_data: InternalPhaseData;
    current_phase_data: InternalPhaseData; // Though not directly used in the DAIDE translation logic here
}
interface InternalGameStatusUpdateNotification extends InternalBaseNotification {
    __type__: "GameStatusUpdate";
    status: string;
}
interface InternalGameMessageReceivedNotification extends InternalBaseNotification {
    __type__: "GameMessageReceived";
    message: { sender: string; recipient: string; message: string; phase?: string; }; // Simplified message structure
}
interface InternalPhaseData {
    state: { name: string /* phase name */ };
    orders: Record<string, string[]>; // power_name -> orders list
    results: Record<string, any[]>; // unit_str -> results list (result objects need .code)
}

// Placeholder for OrderSplitter and related types
interface OrderSplit { unit: string; order_type: string; supported_unit?: string; /* other fields */ }
const OrderSplitterPlaceholder = (orderString: string): OrderSplit => {
    // Very simplified placeholder
    const parts = orderString.split(' ');
    if (parts.length === 1) return { unit: '', order_type: parts[0], length: 1} as any; // For WAIVE FRA
    return { unit: `${parts[0]} ${parts[1]}`, order_type: parts[2], length: parts.length } as any;
};
const OK_RESULT_CODE = 0; // from diplomacy.utils.order_results

// Placeholder for diploStrings
const diploStrings = {
    ACTIVE: "ACTIVE",
    COMPLETED: "COMPLETED",
    CANCELED: "CANCELED",
    // ... other strings
};

// Logger
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};


function _buildActiveNotificationsTs(
    current_phase: string,
    powers: EnginePower[],
    map_name: string,
    deadline: number
): DaideNotification[] {
    const notifs: DaideNotification[] = [];

    const power_centers: Record<string, string[]> = {};
    powers.forEach(p => power_centers[p.name] = p.centers);
    notifs.push(new SupplyCenterNotificationTs(power_centers, map_name));

    const units: Record<string, string[]> = {};
    powers.forEach(p => units[p.name] = p.units);
    const retreats: Record<string, Record<string, string[]>> = {};
    powers.forEach(p => retreats[p.name] = p.retreats);
    notifs.push(new CurrentPositionNotificationTs(current_phase, units, retreats));

    notifs.push(new TimeToDeadlineNotificationTs(deadline));
    return notifs;
}

function _buildCompletedNotificationsTs(
    server_users: any, // Placeholder for server.users
    has_draw_vote: boolean,
    powers: EnginePower[],
    state_history: any // Placeholder for state_history object
): DaideNotification[] {
    const notifs: DaideNotification[] = [];

    if (has_draw_vote) {
        notifs.push(new DrawNotificationTs());
    } else {
        const winners = powers.filter(p => p.units && p.units.length > 0).map(p => p.name);
        if (winners.length === 1) {
            notifs.push(new SoloNotificationTs(winners[0]));
        }
    }

    const last_phase_name = state_history.last_value().name; // Assuming last_value().name gives phase string

    const daideUsers: (DaideUser | null)[] = powers.map(power => {
        const controller = power.get_controller();
        const user = controller ? server_users.get_user(controller) : null; // Assuming get_user
        return (user && 'passcode' in user) ? user as DaideUser : null; // Check if it's a DaideUser
    });

    const powers_year_of_elimination: Record<string, number | null> = {};
    powers.forEach(p => powers_year_of_elimination[p.name] = null);

    // Simplified year of elimination logic
    for (const phaseKey in state_history.items()) { // Assuming items() gives phases
        const state = state_history.items()[phaseKey];
        const phaseName = state.name; // Assuming phase string is state.name
        const year = parseInt(phaseName.substring(1,5), 10); // Extract year

        Object.entries(state.units as Record<string, string[]>).forEach(([power_name, unit_list]) => {
            if (!powers_year_of_elimination[power_name] && (!unit_list || unit_list.length === 0 || unit_list.every(u => u.startsWith('*')))) {
                powers_year_of_elimination[power_name] = year;
            }
        });
    }
    const sortedPowerNames = Object.keys(powers_year_of_elimination).sort();
    const years_of_elimination = sortedPowerNames.map(pn => powers_year_of_elimination[pn]);

    notifs.push(new SummaryNotificationTs(last_phase_name, powers, daideUsers, years_of_elimination));
    notifs.push(new TurnOffNotificationTs());

    return notifs;
}


function onProcessedNotificationTs(
    server: MasterServer,
    notification: InternalGameProcessedNotification,
    connection_handler: ConnectionHandlerTs,
    game: DiplomacyGame
): DaideNotification[] | null {
    const userInfo = get_user_connection(server.users, game, connection_handler);
    const power_name = userInfo.power_name;
    if (!power_name) return [];

    const previous_phase_data = notification.previous_phase_data;
    const previous_state = previous_phase_data.state;
    const previous_phase_name = previous_state.name; // e.g. S1901M
    const previous_phase_type = previous_phase_name.slice(-1); // M, R, A

    const sortedPowerNames = Object.keys(game.powers).sort();
    const powersList = sortedPowerNames.map(pn => game.powers[pn]);

    let notifs: DaideNotification[] = [];

    const powerOrders = previous_phase_data.orders[power_name] || [];
    for (const orderStr of powerOrders) {
        const orderSplit = OrderSplitterPlaceholder(orderStr); // Use placeholder
        let orderUnit = orderSplit.unit;
        let orderResultsData = previous_phase_data.results[orderUnit] || [];

        if (orderSplit.length === 1) { // WAIVE
            // orderSplit.order_type = `${power_name} ${orderSplit.order_type}`; // Python mutates this
            orderResultsData = [{ code: OK_RESULT_CODE }]; // Simulate OK result
        } else {
            // orderSplit.unit = `${power_name} ${orderSplit.unit}`;
        }
        // if (orderSplit.supported_unit) {
        //     orderSplit.supported_unit = `${power_name} ${orderSplit.supported_unit}`;
        // }

        // Create a new OrderSplit-like object for parse_order_to_bytes_ts
        const daideOrderSplit = {
            unit: orderSplit.length === 1 ? power_name : `${power_name} ${orderSplit.unit}`,
            order_type: orderSplit.length === 1 ? orderSplit.order_type.split(' ')[1] : order_split.order_type, // "WAIVE" or "H"
            supported_unit: orderSplit.supported_unit ? `${power_name} ${orderSplit.supported_unit}` : undefined,
            // ... other fields for destination, via_flag etc. would be needed
            length: orderSplit.length,
        };


        const order_bytes = parse_order_to_bytes_ts(previous_phase_type, daideOrderSplit as any); // Cast for placeholder
        notifs.push(new OrderResultNotificationTs(previous_phase_name, order_bytes, orderResultsData.map(r => r.code)));
    }

    if (game.status === diploStrings.ACTIVE) {
        notifs = notifs.concat(_buildActiveNotificationsTs(game.get_current_phase(), powersList, game.map_name, game.deadline));
    } else if (game.status === diploStrings.COMPLETED) {
        notifs = notifs.concat(_buildCompletedNotificationsTs(server.users, game.has_draw_vote(), powersList, game.state_history));
    }
    return notifs;
}

function onStatusUpdateNotificationTs(
    server: MasterServer,
    notification: InternalGameStatusUpdateNotification,
    connection_handler: ConnectionHandlerTs,
    game: DiplomacyGame
): DaideNotification[] | null {
    const userInfo = get_user_connection(server.users, game, connection_handler);
    const power_name = userInfo.power_name;
    const daide_user = userInfo.daide_user as DaideUser | null; // Cast from placeholder
    if (!power_name || !daide_user) return [];

    const sortedPowerNames = Object.keys(game.powers).sort();
    const powersList = sortedPowerNames.map(pn => game.powers[pn]);
    let notifs: DaideNotification[] = [];

    if (notification.status === diploStrings.ACTIVE && game.get_current_phase() === 'S1901M') {
        notifs.push(new HelloNotificationTs(power_name, daide_user.passcode, DEFAULT_LEVEL, game.deadline, game.rules));
        notifs = notifs.concat(_buildActiveNotificationsTs(game.get_current_phase(), powersList, game.map_name, game.deadline));
    } else if (notification.status === diploStrings.COMPLETED) {
        notifs = notifs.concat(_buildCompletedNotificationsTs(server.users, game.has_draw_vote(), powersList, game.state_history));
    } else if (notification.status === diploStrings.CANCELED) {
        notifs.push(new TurnOffNotificationTs());
    }
    return notifs;
}

function onMessageReceivedNotificationTs(
    server: MasterServer,
    notification: InternalGameMessageReceivedNotification,
    connection_handler: ConnectionHandlerTs,
    game: DiplomacyGame
): DaideNotification[] | null {
    const msg = notification.message;
    // DAIDE FRM takes a list of recipients. If internal message is direct, wrap recipient in array.
    const recipients = (msg.recipient === "GLOBAL" || msg.recipient === "ALL")
        ? Object.keys(game.powers).filter(p => p !== msg.sender) // Example: all other powers for GLOBAL
        : [msg.recipient];
    return [new MessageFromNotificationTs(msg.sender, recipients, msg.message)];
}


const DAIDE_NOTIFICATION_TRANSLATOR_MAP: Record<string, Function> = {
  "GameProcessed": onProcessedNotificationTs,
  "GameStatusUpdate": onStatusUpdateNotificationTs,
  "GameMessageReceived": onMessageReceivedNotificationTs,
};

export function translateToDaideNotification(
    server: MasterServer,
    internal_notification: InternalBaseNotification, // Base type for internal notifications
    connection_handler: ConnectionHandlerTs
): DaideNotification[] | null {
    const handler = DAIDE_NOTIFICATION_TRANSLATOR_MAP[internal_notification.__type__];
    if (!handler) {
        logger.debug(`No DAIDE translator for internal notification type: ${internal_notification.__type__}`);
        return null;
    }
    const game = server.get_game(internal_notification.game_id);
    if (!game) {
        logger.warn(`Game not found for DAIDE notification translation: ${internal_notification.game_id}`);
        return null;
    }
    return handler(server, internal_notification, connection_handler, game);
}
