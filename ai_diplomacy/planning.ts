import * as dotenv from 'dotenv';

// Assuming placeholder interfaces and utility functions from other .ts files
import { DiplomacyAgent } from './agent'; // Assuming agent.ts exports this
import { GameHistory } from './game_history'; // Assuming game_history.ts exports this
import { BaseModelClient } from './clients'; // Assuming clients.ts exports this

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

// Placeholders for diplomacy Game object
interface DiplomacyGame {
  powers: Record<string, { is_eliminated: () => boolean }>;
  current_short_phase: string;
  get_state(): any;
  // other Game methods and properties...
}

// Placeholder for gather_possible_orders (from utils.py or utils.ts)
function gather_possible_orders(game: DiplomacyGame, power_name: string): Record<string, string[]> {
  logger.warn(`gather_possible_orders called for ${power_name}. Placeholder implementation.`);
  // Return a dummy value that allows the logic to proceed
  return { [`${power_name.substring(0,3)} LOC`]: [`${power_name.substring(0,3)} LOC H`] };
}

// Type for model_error_stats (already defined in negotiations.ts, ideally should be in a shared types file)
type ModelErrorStats = Record<string, Record<string, number>>;


export async function planning_phase(
    game: DiplomacyGame,
    agents: Record<string, DiplomacyAgent>,
    game_history: GameHistory,
    model_error_stats: ModelErrorStats,
    log_file_path: string,
): Promise<GameHistory> {
    logger.info(`Starting planning phase for ${game.current_short_phase}...`);

    const active_powers = Object.entries(game.powers)
        .filter(([_, p_obj]) => !p_obj.is_eliminated())
        .map(([p_name, _]) => p_name);

    const eliminated_powers = Object.entries(game.powers)
        .filter(([_, p_obj]) => p_obj.is_eliminated())
        .map(([p_name, _]) => p_name);

    logger.info(`Active powers for planning: ${active_powers.join(', ')}`);
    if (eliminated_powers.length > 0) {
        logger.info(`Eliminated powers (skipped): ${eliminated_powers.join(', ')}`);
    } else {
        logger.info("No eliminated powers yet.");
    }

    const board_state = game.get_state();

    const planning_promises = active_powers.map(async (power_name) => {
        if (!agents[power_name]) {
            logger.warn(`Agent for ${power_name} not found in planning phase. Skipping.`);
            return { power_name, status: 'skipped', plan_result: null, error: null };
        }
        const agent = agents[power_name];
        const client = agent.client as BaseModelClient; // Cast, assuming client is compatible

        try {
            logger.debug(`Submitting get_plan task for ${power_name}.`);
            const plan_result = await client.get_plan(
                game as any, // Cast if DiplomacyGame type isn't perfectly matching
                board_state,
                power_name,
                // gather_possible_orders(game, power_name), // get_plan in clients.ts doesn't take possible_orders
                game_history,
                log_file_path, // Pass log_file_path
                agent.goals,
                agent.relationships,
                agent.format_private_diary_for_prompt(),
            );
            return { power_name, status: 'fulfilled', plan_result, error: null };
        } catch (e: any) {
            logger.error(`Exception during get_plan for ${power_name}: ${e.message}`, e);
            return { power_name, status: 'rejected', plan_result: null, error: e };
        }
    });

    logger.info(`Waiting for ${planning_promises.length} planning results...`);
    const results = await Promise.allSettled(planning_promises);

    results.forEach(settled_result => {
        if (settled_result.status === 'fulfilled') {
            const { power_name, status: promise_status, plan_result, error } = settled_result.value;

            if (promise_status === 'skipped') return;

            if (error) { // Error caught and returned from the mapped async function
                logger.error(`Planning failed for ${power_name} (returned error): ${error.message}`, error);
                model_error_stats[power_name] = model_error_stats[power_name] || {};
                model_error_stats[power_name]['planning_execution_errors'] = (model_error_stats[power_name]['planning_execution_errors'] || 0) + 1;
            } else if (plan_result && typeof plan_result === 'string') {
                if (plan_result.startsWith("Error:")) {
                     logger.warn(`Agent ${power_name} reported an error during planning: ${plan_result}`);
                     model_error_stats[power_name] = model_error_stats[power_name] || {};
                     model_error_stats[power_name]['planning_generation_errors'] = (model_error_stats[power_name]['planning_generation_errors'] || 0) + 1;
                } else if (plan_result.trim() !== "") {
                    const agent = agents[power_name];
                    agent.add_journal_entry(`Generated plan for ${game.current_short_phase}: ${plan_result.substring(0,100)}...`);
                    game_history.add_plan(
                        game.current_short_phase, power_name, plan_result
                    );
                    logger.debug(`Added plan for ${power_name} to history.`);
                } else {
                    logger.warn(`Agent ${power_name} returned an empty plan.`);
                }
            } else {
                 logger.warn(`Agent ${power_name} returned null or invalid plan result: ${plan_result}`);
            }
        } else { // settled_result.status === 'rejected' - should not happen if errors are caught inside the map
            const reason = (settled_result as PromiseRejectedResult).reason;
            logger.error(`A planning promise was unexpectedly rejected: ${reason}`, reason);
            // Cannot easily map to power_name here unless we add it to the rejection or process by index
        }
    });

    logger.info("Planning phase processing complete.");
    return game_history;
}
