import * as dotenv from 'dotenv';

// Assuming placeholder interfaces and utility functions from other .ts files
import { DiplomacyAgent } from './agent'; // Assuming agent.ts exports this
import { BaseModelClient } from './clients'; // Assuming clients.ts exports this
import { GameHistory } from './game_history'; // Assuming game_history.ts exports this

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

// Placeholders for diplomacy Game object and Message type
interface DiplomacyGame {
  powers: Record<string, { is_eliminated: () => boolean }>;
  current_short_phase: string;
  get_state(): any;
  add_message(message: DiplomacyMessage): void;
  // other Game methods and properties...
}

// Represents the message structure expected by the diplomacy game engine
interface DiplomacyMessage {
  phase: string;
  sender: string;
  recipient: string;
  message: string; // content of the message
  time_sent?: Date | null; // Optional, engine might assign
}

const GLOBAL_RECIPIENT = "GLOBAL"; // Diplomacy library might use 'ALL' or 'GLOBAL'

// Placeholder for gather_possible_orders (from utils.py)
function gather_possible_orders(game: DiplomacyGame, power_name: string): Record<string, string[]> {
  logger.warn(`gather_possible_orders called for ${power_name}. Placeholder implementation.`);
  // Return a dummy value that allows the logic to proceed
  return { [`${power_name.substring(0,3)} LOC`]: [`${power_name.substring(0,3)} LOC H`] };
}

// Type for model_error_stats
type ModelErrorStats = Record<string, Record<string, number>>;

export async function conduct_negotiations(
    game: DiplomacyGame,
    agents: Record<string, DiplomacyAgent>,
    game_history: GameHistory,
    model_error_stats: ModelErrorStats,
    log_file_path: string,
    max_rounds: number = 3,
): Promise<GameHistory> {
    logger.info("Starting negotiation phase.");

    const active_powers = Object.entries(game.powers)
        .filter(([_, p_obj]) => !p_obj.is_eliminated())
        .map(([p_name, _]) => p_name);

    const eliminated_powers = Object.entries(game.powers)
        .filter(([_, p_obj]) => p_obj.is_eliminated())
        .map(([p_name, _]) => p_name);

    logger.info(`Active powers for negotiations: ${active_powers.join(', ')}`);
    if (eliminated_powers.length > 0) {
        logger.info(`Eliminated powers (skipped): ${eliminated_powers.join(', ')}`);
    } else {
        logger.info("No eliminated powers yet.");
    }

    for (let round_index = 0; round_index < max_rounds; round_index++) {
        logger.info(`Negotiation Round ${round_index + 1}/${max_rounds}`);

        const tasks: Array<Promise<any>> = []; // Using 'any' for result type from get_conversation_reply
        const power_names_for_tasks: string[] = [];

        for (const power_name of active_powers) {
            if (!agents[power_name]) {
                logger.warn(`Agent for ${power_name} not found in negotiations. Skipping.`);
                continue;
            }
            const agent = agents[power_name];
            const client = agent.client as BaseModelClient; // Cast to BaseModelClient

            const possible_orders = gather_possible_orders(game, power_name);
            if (Object.keys(possible_orders).length === 0) {
                logger.info(`No orderable locations for ${power_name}; skipping message generation.`);
                continue;
            }
            const board_state = game.get_state();

            tasks.push(
                client.get_conversation_reply(
                    game as any, // Cast game to any if its type doesn't perfectly match client method expectations
                    board_state,
                    power_name,
                    possible_orders,
                    game_history,
                    game.current_short_phase,
                    log_file_path,
                    active_powers,
                    agent.goals,
                    agent.relationships,
                    agent.format_private_diary_for_prompt(),
                )
            );
            power_names_for_tasks.push(power_name);
            logger.debug(`Prepared get_conversation_reply task for ${power_name}.`);
        }

        let results: Array<any> = [];
        if (tasks.length > 0) {
            logger.debug(`Running ${tasks.length} conversation tasks concurrently...`);
            // Promise.allSettled is similar to asyncio.gather with return_exceptions=True
            const settled_results = await Promise.allSettled(tasks);
            results = settled_results.map(res => {
                if (res.status === 'fulfilled') return res.value;
                if (res.status === 'rejected') return res.reason; // This will be the error object
                return null; // Should not happen
            });
        } else {
            logger.debug("No conversation tasks to run for this round.");
        }

        for (let i = 0; i < results.length; i++) {
            const power_name = power_names_for_tasks[i];
            const agent = agents[power_name];
            const model_name = (agent.client as BaseModelClient).model_name;
            const result = results[i];

            let messages: Array<Record<string, string>> = [];

            if (result instanceof Error) {
                logger.error(`Error getting conversation reply for ${power_name}: ${result.message}`, result);
                model_error_stats[model_name] = model_error_stats[model_name] || {};
                model_error_stats[model_name]["conversation_errors"] = (model_error_stats[model_name]["conversation_errors"] || 0) + 1;
            } else if (result === null || result === undefined) { // Check for null or undefined
                 logger.warn(`Received null/undefined instead of messages for ${power_name}.`);
                 model_error_stats[model_name] = model_error_stats[model_name] || {};
                 model_error_stats[model_name]["conversation_errors"] = (model_error_stats[model_name]["conversation_errors"] || 0) + 1;
            } else {
                messages = result as Array<Record<string, string>>; // Cast result
                logger.debug(`Received ${messages.length} message(s) from ${power_name}.`);
            }

            if (messages && messages.length > 0) {
                for (const message_data of messages) {
                    if (typeof message_data !== 'object' || !message_data.content) {
                        logger.warn(`Invalid message format received from ${power_name}: ${JSON.stringify(message_data)}. Skipping.`);
                        continue;
                    }

                    let recipient = GLOBAL_RECIPIENT;
                    if (message_data.message_type === "private") {
                        recipient = message_data.recipient || GLOBAL_RECIPIENT;
                        if (!game.powers[recipient] && recipient !== GLOBAL_RECIPIENT) {
                            logger.warn(`Invalid recipient '${recipient}' in message from ${power_name}. Sending globally.`);
                            recipient = GLOBAL_RECIPIENT;
                        }
                    }

                    const diplo_message: DiplomacyMessage = {
                        phase: game.current_short_phase,
                        sender: power_name,
                        recipient: recipient,
                        message: message_data.content || "",
                        time_sent: null, // Engine assigns time
                    };
                    game.add_message(diplo_message);
                    game_history.add_message(
                        game.current_short_phase,
                        power_name,
                        recipient,
                        message_data.content || "",
                    );
                    const journal_recipient = recipient !== GLOBAL_RECIPIENT ? `to ${recipient}` : "globally";
                    agent.add_journal_entry(`Sent message ${journal_recipient} in ${game.current_short_phase}: ${(message_data.content || "").substring(0,100)}...`);
                    logger.info(`[${power_name} -> ${recipient}] ${(message_data.content || "").substring(0,100)}...`);
                }
            } else {
                logger.debug(`No valid messages returned or error occurred for ${power_name}.`);
            }
        }
    }
    logger.info("Negotiation phase complete.");
    return game_history;
}
