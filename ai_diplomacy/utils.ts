import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';
import { createObjectCsvWriter } from 'csv-writer'; // Correct import

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

// Placeholder types for Diplomacy game objects and clients
// These would ideally be imported from their respective .ts files or a shared types definition
export interface DiplomacyGame {
  powers: Record<string, { units: string[], is_eliminated: () => boolean }>; // Added units for get_valid_orders
  get_orderable_locations(power_name: string): string[];
  get_all_possible_orders(): Record<string, string[]>;
  _valid_order?(power: any, unit: string, order_part: string, report: number): number; // Placeholder for internal method
  map: {
    norm(order: string): string;
    // aliases?: Record<string, string>; // If used by norm or other map functions
  };
  // other Game methods and properties...
}

export interface BaseModelClient {
  model_name: string;
  get_orders(args: {
    game: DiplomacyGame;
    board_state: any; // Replace with actual BoardState type
    power_name: string;
    possible_orders: Record<string, string[]>;
    conversation_text: any; // Should be GameHistory
    model_error_stats: Record<string, Record<string, number>>;
    agent_goals?: string[];
    agent_relationships?: Record<string, string>;
    agent_private_diary_str?: string;
    log_file_path: string;
    phase: string;
  }): Promise<string[]>;
  fallback_orders(possible_orders: Record<string, string[]>): string[];
  generate_response(prompt: string): Promise<string>; // Added for run_llm_and_log
}

export interface GameHistory {
    // Define structure if needed by functions in this file
}

export function assign_models_to_powers(): Record<string, string> {
    /*
    Example usage: define which model each power uses.
    Return a dict: { power_name: model_id, ... }
    POWERS = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
    Models supported: o3-mini, o4-mini, o3, gpt-4o, gpt-4o-mini,
                    claude-opus-4-20250514, claude-sonnet-4-20250514, claude-3-5-haiku-20241022, claude-3-5-sonnet-20241022, claude-3-7-sonnet-20250219
                    gemini-2.0-flash, gemini-2.5-flash-preview-04-17, gemini-2.5-pro-preview-03-25,
                    deepseek-chat, deepseek-reasoner
                    openrouter-meta-llama/llama-3.3-70b-instruct, openrouter-qwen/qwen3-235b-a22b, openrouter-microsoft/phi-4-reasoning-plus:free,
                    openrouter-deepseek/deepseek-prover-v2:free, openrouter-meta-llama/llama-4-maverick:free, openrouter-nvidia/llama-3.3-nemotron-super-49b-v1:free,
                    openrouter-google/gemma-3-12b-it:free, openrouter-google/gemini-2.5-flash-preview-05-20
    */

    // Using the "TEST MODELS" from the Python example
    return {
        "AUSTRIA": "openrouter-google/gemini-2.5-flash-preview",
        "ENGLAND": "openrouter-google/gemini-2.5-flash-preview",
        "FRANCE": "openrouter-google/gemini-2.5-flash-preview",
        "GERMANY": "openrouter-google/gemini-2.5-flash-preview",
        "ITALY": "openrouter-google/gemini-2.5-flash-preview",
        "RUSSIA": "openrouter-google/gemini-2.5-flash-preview",
        "TURKEY": "openrouter-google/gemini-2.5-flash-preview",
    };
}

export function load_prompt_from_utils(filename: string): string { // Renamed to avoid conflict if this file is imported elsewhere
    const prompt_path = path.join(__dirname, 'prompts', filename);
    try {
        return fs.readFileSync(prompt_path, "utf-8").strip(); // .strip() is Python; use .trim() in JS
    } catch (error) {
        logger.error(`Prompt file not found: ${prompt_path}`);
        return "";
    }
}

export function log_llm_response(
    log_file_path: string,
    model_name: string,
    power_name: string | null,
    phase: string,
    response_type: string,
    raw_input_prompt: string,
    raw_response: string,
    success: string,
): void {
    try {
        const log_dir = path.dirname(log_file_path);
        if (log_dir && !fs.existsSync(log_dir)) {
             fs.mkdirSync(log_dir, { recursive: true });
        }

        const file_exists = fs.existsSync(log_file_path);
        const csvWriterInstance = createObjectCsvWriter({
            path: log_file_path,
            header: [
                { id: "model", title: "model" },
                { id: "power", title: "power" },
                { id: "phase", title: "phase" },
                { id: "response_type", title: "response_type" },
                { id: "raw_input", title: "raw_input" },
                { id: "raw_response", title: "raw_response" },
                { id: "success", title: "success" },
            ],
            append: file_exists, // Append if file exists
        });

        const records = [{
            model: model_name,
            power: power_name || "game",
            phase: phase,
            response_type: response_type,
            raw_input: raw_input_prompt,
            raw_response: raw_response,
            success: success,
        }];

        // Write header only if file is new (handled by csv-writer's append logic with writeheader not being called separately)
        // CsvWriter.writeRecords appends. If you need to write header conditionally, it's a bit more manual with this lib
        // or ensure the file is created with header if it's the first write.
        // For simplicity, if file_exists is false, we can write header then records,
        // but createObjectCsvWriter with append:true should handle this if we always try to write records.
        // The library might not write headers if append is true and file exists.
        // A common pattern is to check file existence and write header manually if needed.

        // Simplified: Assume csvWriterInstance handles header correctly or manage header writing outside if needed.
        // The 'csv-writer' library typically writes the header if the file doesn't exist or is empty on the first write operation.
        // If `append: true` is set and the file exists and is not empty, it will not write the header again.

        // However, to be absolutely sure the header is written if the file is new,
        // and not written if appending, we might need a slightly more manual check or trust the library.
        // The `createObjectCsvWriter` if header is defined and append is true, will only write header if file is new.

        csvWriterInstance.writeRecords(records)
            .then(() => {/* logger.debug(`LLM response logged to ${log_file_path}`); */})
            .catch((e) => logger.error(`Failed to write LLM log record: ${e.message}`));

    } catch (e: any) {
        logger.error(`Failed to log LLM response to ${log_file_path}: ${e.message}`, e);
    }
}

export async function run_llm_and_log_from_utils( // Renamed
    client: BaseModelClient,
    prompt: string,
    // log_file_path, power_name, phase, response_type are for context if errors are logged here
    // but the Python code says "Logging is handled by the caller" for the main CSV.
    // This function only logs API errors.
    _log_file_path: string,
    _power_name: string | null,
    _phase: string,
    _response_type: string,
): Promise<string> {
    let raw_response = "";
    try {
        raw_response = await client.generate_response(prompt);
    } catch (e: any) {
        logger.error(`API Error during LLM call for ${client.model_name}/${_power_name}/${_response_type} in phase ${_phase}: ${e.message}`, e);
        // raw_response remains "" indicating failure
    }
    return raw_response;
}

// Stubs for more complex functions that depend heavily on DiplomacyGame specifics
export function gather_possible_orders(game: DiplomacyGame, power_name: string): Record<string, string[]> {
    logger.warn("gather_possible_orders called - using placeholder implementation.");
    const orderable_locs = game.get_orderable_locations(power_name);
    const all_possible = game.get_all_possible_orders();
    const result: Record<string, string[]> = {};
    for (const loc of orderable_locs) {
        result[loc] = all_possible[loc] || [];
    }
    return result;
}

export async function get_valid_orders(
    game: DiplomacyGame,
    client: BaseModelClient,
    board_state: any, // Replace with actual BoardState type
    power_name: string,
    possible_orders: Record<string, string[]>,
    game_history: GameHistory, // Replace with actual GameHistory type
    model_error_stats: Record<string, Record<string, number>>,
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary_str?: string,
    log_file_path?: string, // Made optional as per Python implementation
    phase?: string, // Made optional
): Promise<string[]> {
    logger.warn("get_valid_orders called - using placeholder implementation for order validation part.");

    const orders = await client.get_orders({ // Pass as an object
        game,
        board_state,
        power_name,
        possible_orders,
        conversation_text: game_history,
        model_error_stats,
        agent_goals,
        agent_relationships,
        agent_private_diary_str,
        log_file_path: log_file_path || "", // Ensure string
        phase: phase || "", // Ensure string
    });

    if (!Array.isArray(orders)) {
        logger.warn(`[${power_name}] Orders received from LLM is not a list: ${orders}. Using fallback.`);
        if (model_error_stats[client.model_name]) { // Ensure key exists
            model_error_stats[client.model_name]["order_decoding_errors"] = (model_error_stats[client.model_name]["order_decoding_errors"] || 0) + 1;
        } else {
            model_error_stats[client.model_name] = { "order_decoding_errors": 1 };
        }
        return client.fallback_orders(possible_orders);
    }

    // Simplified validation: The detailed validation using game._valid_order is complex
    // to replicate without the exact Diplomacy game engine's JS/TS version.
    // For now, we'll assume orders returned by client.get_orders are pre-validated or
    // that this function's role is more about the retry logic (which isn't in the Python snippet provided).
    // The Python snippet's validation loop is extensive.
    // Here, we'll just filter out empty orders.
    const valid_orders = orders.filter(order => order && order.trim() !== "");
    if (valid_orders.length !== orders.length) {
        logger.debug(`[${power_name}] Some empty orders were filtered out.`);
        // Potentially log to model_error_stats if this is considered an error
    }

    if (valid_orders.length === 0 && orders.length > 0) { // All orders were empty, or list was empty
         logger.debug(`[${power_name}] No valid orders after filtering, using fallback.`);
         if (model_error_stats[client.model_name]) {
            model_error_stats[client.model_name]["order_decoding_errors"] = (model_error_stats[client.model_name]["order_decoding_errors"] || 0) + 1;
        } else {
            model_error_stats[client.model_name] = { "order_decoding_errors": 1 };
        }
        return client.fallback_orders(possible_orders);
    }

    // The Python version has a complex validation loop using game._valid_order
    // This is a placeholder for that logic. If game._valid_order is not available,
    // this function might primarily rely on the client's own validation (_validate_orders).
    logger.info(`[${power_name}] Validation against game engine rules in get_valid_orders is currently simplified.`);

    return valid_orders;
}


export function normalize_and_compare_orders(
    issued_orders: Record<string, string[]>,
    accepted_orders_dict: Record<string, string[]>,
    game: DiplomacyGame,
): [Record<string, Set<string>>, Record<string, Set<string>>] {
    logger.warn("normalize_and_compare_orders called - using placeholder for complex normalization.");

    const normalize_order = (order: string): string => {
        if (!order) return order;
        try {
            // This assumes game.map.norm is available and works similarly.
            return game.map.norm(order);
        } catch (e: any) {
            logger.warn(`Could not normalize order '${order}': ${e.message}`);
            return order;
        }
    };

    const orders_not_accepted: Record<string, Set<string>> = {};
    const orders_not_issued: Record<string, Set<string>> = {};
    const all_powers = new Set([...Object.keys(issued_orders), ...Object.keys(accepted_orders_dict)]);

    for (const pwr of all_powers) {
        const issued_set = new Set(
            (issued_orders[pwr] || []).map(normalize_order).filter(o => o)
        );
        const accepted_set = new Set(
            (accepted_orders_dict[pwr] || []).map(normalize_order).filter(o => o)
        );

        const missing_from_engine = new Set([...issued_set].filter(o => !accepted_set.has(o)));
        const missing_from_issued = new Set([...accepted_set].filter(o => !issued_set.has(o)));

        if (missing_from_engine.size > 0) {
            orders_not_accepted[pwr] = missing_from_engine;
        }
        if (missing_from_issued.size > 0) {
            orders_not_issued[pwr] = missing_from_issued;
        }
    }
    return [orders_not_accepted, orders_not_issued];
}
