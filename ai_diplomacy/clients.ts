import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';
import { JSONPath } from 'jsonpath-plus'; // For advanced JSON path finding, if needed for _extract_moves

// Assuming placeholder interfaces and utility functions from agent.ts or similar
// These would be properly imported from their respective files in a complete conversion.

// Placeholders from agent.ts (or should be from a shared types file)
interface Game {
  current_short_phase: string;
  get_state(): any;
  get_current_phase(): string;
  get_all_possible_orders(): Record<string, string[]>; // Updated to reflect usage
  powers: string[];
  get_messages_by_phase(phaseName: string): Array<{ sender: string; recipient: string; content: string }>;
}

interface GameHistory {
  get_messages_this_round(power_name: string, current_phase_name: string): string;
  get_ignored_messages_by_power(power_name: string): Record<string, Array<{ phase: string; content: string }>>;
  phases: Array<{ name: string }>;
  get_messages_by_phase(phase_name: string): Array<{ sender: string; recipient: string; content: string }>;
  // Added based on usage in build_conversation_prompt
  get_recent_messages_to_power(power_name: string, limit?: number): Array<{ sender: string; recipient: string; phase: string; content: string }>;
}

// Placeholder for utility functions (assuming they exist in a utils.ts or similar)
const load_prompt = (filename: string): string | null => {
  // Basic placeholder using fs, similar to _load_prompt_file in agent.ts
  try {
    const currentDir = __dirname; // This might need adjustment based on execution context
    const promptsDir = path.join(currentDir, 'prompts'); // Assuming prompts are in a 'prompts' subdirectory
    const filepath = path.join(promptsDir, filename);
    if (fs.existsSync(filepath)) {
      return fs.readFileSync(filepath, 'utf-8');
    }
    // Fallback to prompts relative to project root if not found in local prompts
     const projectRootPromptsDir = path.join(process.cwd(), 'ai_diplomacy', 'prompts');
     const projectRootFilepath = path.join(projectRootPromptsDir, filename);
     if (fs.existsSync(projectRootFilepath)) {
       return fs.readFileSync(projectRootFilepath, 'utf-8');
     }
    logger.error(`Prompt file not found at ${filepath} or ${projectRootFilepath}`);
    return null;
  } catch (e: any) {
    logger.error(`Error loading prompt file ${filename}: ${e.message}`);
    return null;
  }
};

// Placeholder for run_llm_and_log
const run_llm_and_log = async (args: {
  client: BaseModelClient; // The client instance itself
  prompt: string;
  log_file_path: string;
  power_name: string;
  phase: string;
  response_type: string;
}): Promise<string> => {
  logger.debug(`[run_llm_and_log] Called by ${args.power_name} for ${args.response_type} in phase ${args.phase}. Prompt: ${args.prompt.substring(0,100)}...`);
  // In a real scenario, this would call the client's generate_response and add logging, retries, etc.
  // For now, it directly calls generate_response for simplicity in this context.
  try {
    const response = await args.client.generate_response(args.prompt);
    // Basic logging of success, actual log_llm_response would be more detailed
    logger.info(`[run_llm_and_log] LLM call for ${args.power_name} (${args.response_type}) successful.`);
    return response;
  } catch (error: any) {
    logger.error(`[run_llm_and_log] LLM call for ${args.power_name} (${args.response_type}) failed: ${error.message}`);
    // log_llm_response would be called here with failure details
    throw error; // Re-throw to be caught by the calling method
  }
};

// Placeholder for log_llm_response
const log_llm_response = (args: {
  log_file_path: string;
  model_name: string;
  power_name: string;
  phase: string;
  response_type: string;
  raw_input_prompt: string;
  raw_response: string;
  success: string;
  // token_usage and cost can be added later
}) => {
  logger.info(`[log_llm_response] Logging for ${args.power_name}, Type: ${args.response_type}, Success: ${args.success}`);
  // Actual implementation would write to a CSV or structured log.
};

// Placeholder for prompt_constructor functions
const construct_order_generation_prompt = (args: any): string => {
    logger.warn("construct_order_generation_prompt called. Placeholder implementation.");
    return `Placeholder order generation prompt for ${args.power_name}`;
};

const build_context_prompt = (args: any): string => {
    logger.warn("build_context_prompt called. Placeholder implementation.");
    return `Placeholder context for ${args.power_name}`;
};


// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

// Type definitions used within clients.py
type PossibleOrders = Record<string, string[]>;
type ModelErrorStats = Record<string, Record<string, number>>; // Simplified

export abstract class BaseModelClient {
  model_name: string;
  system_prompt: string | null;

  constructor(model_name: string) {
    this.model_name = model_name;
    this.system_prompt = load_prompt("system_prompt.txt");
    if (!this.system_prompt) {
        logger.warn(`[${this.model_name}] Failed to load default system_prompt.txt. System prompt will be empty initially.`);
        this.system_prompt = ""; // Ensure it's at least an empty string
    }
  }

  set_system_prompt(content: string): void {
    this.system_prompt = content;
    logger.info(`[${this.model_name}] System prompt updated.`);
  }

  abstract generate_response(prompt: string): Promise<string>;

  // build_context_prompt and construct_order_generation_prompt are now imported or placeholders

  async get_orders(
    game: Game, // Replace with actual Game type if available
    board_state: any, // Replace with actual BoardState type
    power_name: string,
    possible_orders: PossibleOrders,
    game_history: GameHistory, // Was conversation_text
    model_error_stats: ModelErrorStats | null, // Can be null
    log_file_path: string,
    phase: string,
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary_str?: string,
  ): Promise<string[]> {
    const prompt = construct_order_generation_prompt({
        system_prompt: this.system_prompt, // construct_order_generation_prompt should handle if this is null
        game,
        board_state,
        power_name,
        possible_orders,
        game_history,
        agent_goals,
        agent_relationships,
        agent_private_diary_str,
    });

    let raw_response = "";
    let success_status = "Failure: Initialized";
    let parsed_orders_for_return = this.fallback_orders(possible_orders);

    try {
        raw_response = await run_llm_and_log({
            client: this,
            prompt,
            log_file_path,
            power_name,
            phase,
            response_type: 'order',
        });
        logger.debug(
            `[${this.model_name}] Raw LLM response for ${power_name} orders:\n${raw_response}`
        );

        const move_list = this._extract_moves(raw_response, power_name);

        if (!move_list || move_list.length === 0) {
            logger.warn(
                `[${this.model_name}] Could not extract moves for ${power_name}. Using fallback.`
            );
            if (model_error_stats && this.model_name in model_error_stats) {
                model_error_stats[this.model_name] = model_error_stats[this.model_name] || {};
                model_error_stats[this.model_name]["order_decoding_errors"] = (model_error_stats[this.model_name]["order_decoding_errors"] || 0) + 1;
            }
            success_status = "Failure: No moves extracted";
        } else {
            const [validated_moves, invalid_moves_list] = this._validate_orders(move_list, possible_orders);
            logger.debug(`[${this.model_name}] Validated moves for ${power_name}: ${validated_moves}`);
            parsed_orders_for_return = validated_moves;

            if (invalid_moves_list.length > 0) {
                const max_invalid_to_log = 5;
                const display_invalid_moves = invalid_moves_list.slice(0, max_invalid_to_log);
                const omitted_count = invalid_moves_list.length - display_invalid_moves.length;

                let invalid_moves_str = display_invalid_moves.join(", ");
                if (omitted_count > 0) {
                    invalid_moves_str += `, ... (${omitted_count} more)`;
                }
                success_status = `Failure: Invalid LLM Moves (${invalid_moves_list.length}): ${invalid_moves_str}`;
                if (validated_moves.length === 0) {
                     logger.warn(`[${power_name}] All LLM-proposed moves were invalid. Using fallbacks. Invalid: ${invalid_moves_list.join(", ")}`);
                } else {
                    logger.info(`[${power_name}] Some LLM-proposed moves were invalid. Using fallbacks/validated. Invalid: ${invalid_moves_list.join(", ")}`);
                }
            } else {
                success_status = "Success";
            }
        }
    } catch (e: any) {
        logger.error(`[${this.model_name}] LLM error for ${power_name} in get_orders: ${e.message}`, e);
        success_status = `Failure: Exception (${e.constructor.name})`;
    } finally {
        if (log_file_path) {
            log_llm_response({
                log_file_path,
                model_name: this.model_name,
                power_name,
                phase,
                response_type: "order_generation",
                raw_input_prompt: prompt,
                raw_response,
                success: success_status,
            });
        }
    }
    return parsed_orders_for_return;
  }

  private _extract_moves(raw_response: string, power_name: string): string[] | null {
    // Simplified initial implementation of _extract_moves
    // Python version has multiple regex attempts and fallbacks
    logger.debug(`[${this.model_name}] Attempting to extract moves for ${power_name} from raw response of length ${raw_response.length}`);

    const patterns = [
        /PARSABLE OUTPUT:\s*(\{[\s\S]*?\})/is, // Case-insensitive, dotall for content
        /```json\s*([\s\S]*?)\s*```/is,
        /```\s*([\s\S]*?)\s*```/is, // Plain code fence
        /(\{[\s\S]*\orders\s*:\s*\[[\s\S]*?\][\s\S]*?\})/is, // Bare JSON with orders
    ];

    let json_text: string | null = null;

    for (const pattern of patterns) {
        const matches = raw_response.match(pattern);
        if (matches && matches[1]) {
            json_text = matches[1].trim();
            // If it's a code block, it might already be {}.
            // If it's PARSABLE OUTPUT: {content}, group 1 is {content}.
            // If it's bare JSON, group 1 is the JSON.
            logger.debug(`[${this.model_name}] Found potential JSON block with pattern: ${pattern}`);
            break;
        }
    }

    if (!json_text) {
         // Fallback: try to find the largest JSON object in the string
        const jsonObjects = raw_response.match(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g);
        if (jsonObjects && jsonObjects.length > 0) {
            json_text = jsonObjects.reduce((a, b) => (a.length > b.length ? a : b));
            logger.debug(`[${this.model_name}] No specific markers found, using largest found JSON object.`);
        }
    }

    if (!json_text) {
        logger.warn(`[${this.model_name}] No JSON text found in LLM response for ${power_name}.`);
        return null;
    }

    try {
        // Basic cleaning before parsing
        let cleaned_json_text = json_text;
        // Remove trailing commas before } or ]
        cleaned_json_text = cleaned_json_text.replace(/,\s*([}\]])/g, '$1');
        // Replace single quotes with double quotes for keys and simple string values
        // More complex values with escaped quotes might need more robust handling
        cleaned_json_text = cleaned_json_text.replace(/'(\w+)'\s*:/g, '"$1":'); // Keys
        cleaned_json_text = cleaned_json_text.replace(/:\s*'([^']*)'/g, ': "$1"'); // Values

        const data = JSON.parse(cleaned_json_text);
        if (data && data.orders && Array.isArray(data.orders)) {
            return data.orders.filter((order: any) => typeof order === 'string');
        }
        logger.warn(`[${this.model_name}] Parsed JSON does not contain a valid 'orders' array for ${power_name}. Data: ${JSON.stringify(data)}`);
        return null;
    } catch (e: any) {
        logger.warn(`[${this.model_name}] JSON decode failed for ${power_name}: ${e.message}. JSON Text: ${json_text.substring(0, 200)}...`);

        // Python's ast.literal_eval is more forgiving for simple list-like strings.
        // A direct equivalent is hard, but we can try a regex for "orders": [...]
        const bracket_pattern = /["']orders["']\s*:\s*\[([^\]]*)\]/is;
        const bracket_match = json_text.match(bracket_pattern);
        if (bracket_match && bracket_match[1]) {
            try {
                const moves_str = bracket_match[1].trim();
                // Split by comma, then clean up quotes and whitespace for each item
                const moves = moves_str.split(',').map(s => s.replace(/["']/g, '').trim()).filter(s => s.length > 0);
                if (moves.length > 0) {
                     logger.info(`[${this.model_name}] Successfully parsed moves using bracket fallback for ${power_name}.`);
                    return moves;
                }
            } catch (e2: any) {
                logger.warn(`[${this.model_name}] Bracket fallback parse also failed for ${power_name}: ${e2.message}`);
            }
        }
        return null;
    }
  }

  private _validate_orders(
    moves: string[],
    possible_orders: PossibleOrders
  ): [string[], string[]] { // [validated_moves, invalid_moves_found]
    logger.debug(`[${this.model_name}] Proposed LLM moves: ${JSON.stringify(moves)}`);
    const validated: string[] = [];
    const invalid_moves_found: string[] = [];
    const used_locs: Set<string> = new Set();

    if (!Array.isArray(moves)) {
        logger.debug(`[${this.model_name}] Moves not a list, fallback.`);
        return [this.fallback_orders(possible_orders), []];
    }

    const all_possible_order_values: Set<string> = new Set();
    Object.values(possible_orders).forEach(orders_list => {
        orders_list.forEach(order => all_possible_order_values.add(order));
    });

    for (const move_str of moves) {
        if (typeof move_str !== 'string') {
            logger.debug(`[${this.model_name}] Invalid move type from LLM (not a string): ${move_str}`);
            invalid_moves_found.push(String(move_str)); // Store as string for logging
            continue;
        }
        if (all_possible_order_values.has(move_str)) {
            validated.push(move_str);
            const parts = move_str.split(" ");
            if (parts.length >= 2) { // e.g., "A PAR H", "A PAR S A BUD"
                // Location is usually the first 3 chars of the second token for unit orders
                // e.g. A BUD H -> BUD
                used_locs.add(parts[1].substring(0, 3));
            }
        } else {
            logger.debug(`[${this.model_name}] Invalid move from LLM: ${move_str}`);
            invalid_moves_found.push(move_str);
        }
    }

    for (const [loc, orders_list] of Object.entries(possible_orders)) {
        const unit_location = loc.substring(0, 3); // Extract the location part, e.g., "PAR" from "PAR (fleet)"
        if (!used_locs.has(unit_location) && orders_list && orders_list.length > 0) {
            const hold_candidates = orders_list.filter(o => o.endsWith("H"));
            const order_to_add = hold_candidates.length > 0 ? hold_candidates[0] : orders_list[0];
            validated.push(order_to_add);
            used_locs.add(unit_location); // Mark as used even if filled by fallback HOLD
            logger.debug(`[${this.model_name}] Filled missing order for ${unit_location} with ${order_to_add}`);
        }
    }

    // Deduplicate validated orders (e.g., if LLM proposed a HOLD that was also added by fallback)
    const unique_validated = Array.from(new Set(validated));

    if (unique_validated.length === 0 && invalid_moves_found.length > 0) {
        logger.warn(`[${this.model_name}] All LLM moves invalid (${invalid_moves_found.length} found), using fallback. Invalid: ${invalid_moves_found.join(", ")}`);
        return [this.fallback_orders(possible_orders), invalid_moves_found];
    }

    return [unique_validated, invalid_moves_found];
  }

  fallback_orders(possible_orders: PossibleOrders): string[] {
    const fallback: string[] = [];
    for (const orders_list of Object.values(possible_orders)) {
        if (orders_list && orders_list.length > 0) {
            const holds = orders_list.filter(o => o.endsWith("H"));
            fallback.push(holds.length > 0 ? holds[0] : orders_list[0]);
        }
    }
    return fallback;
  }

  // build_planning_prompt, build_conversation_prompt, get_planning_reply, get_conversation_reply, get_plan

  build_planning_prompt(
    game: Game,
    board_state: any,
    power_name: string,
    possible_orders: PossibleOrders, // May not be strictly needed for planning context
    game_history: GameHistory,
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary_str?: string,
  ): string {
    const instructions = load_prompt("planning_instructions.txt");
    if (!instructions) {
        logger.error(`[${this.model_name}] Failed to load planning_instructions.txt.`);
        return "Error: Planning instructions not found."; // Or throw error
    }

    const context = build_context_prompt({ // Using the placeholder
        game,
        board_state,
        power_name,
        possible_orders,
        game_history,
        agent_goals,
        agent_relationships,
        agent_private_diary: agent_private_diary_str,
    });

    return `${context}\n\n${instructions}`;
  }

  build_conversation_prompt(
    game: Game,
    board_state: any,
    power_name: string,
    possible_orders: PossibleOrders,
    game_history: GameHistory,
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary_str?: string,
  ): string {
    const instructions = load_prompt("conversation_instructions.txt");
    if (!instructions) {
        logger.error(`[${this.model_name}] Failed to load conversation_instructions.txt.`);
        return "Error: Conversation instructions not found."; // Or throw
    }

    const context = build_context_prompt({ // Using the placeholder
        game,
        board_state,
        power_name,
        possible_orders,
        game_history,
        agent_goals,
        agent_relationships,
        agent_private_diary: agent_private_diary_str,
    });

    const recent_messages_to_power = game_history.get_recent_messages_to_power ? game_history.get_recent_messages_to_power(power_name, 3) : [];

    logger.info(`[${power_name}] Found ${recent_messages_to_power.length} high priority messages to respond to`);
    if (recent_messages_to_power.length > 0) {
        recent_messages_to_power.forEach((msg, i) => {
            logger.info(`[${power_name}] Priority message ${i+1}: From ${msg.sender} in ${msg.phase}: ${msg.content.substring(0,50)}...`);
        });
    }

    let unanswered_messages = "\n\nRECENT MESSAGES REQUIRING YOUR ATTENTION:\n";
    if (recent_messages_to_power.length > 0) {
        recent_messages_to_power.forEach(msg => {
            unanswered_messages += `\nFrom ${msg.sender} in ${msg.phase}: ${msg.content}\n`;
        });
    } else {
        unanswered_messages += "\nNo urgent messages requiring direct responses.\n";
    }

    return `${context}${unanswered_messages}\n\n${instructions}`;
  }

  async get_planning_reply(
    game: Game,
    board_state: any,
    power_name: string,
    possible_orders: PossibleOrders,
    game_history: GameHistory,
    game_phase: string,
    log_file_path: string,
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary_str?: string,
  ): Promise<string> {
    const prompt = this.build_planning_prompt(
        game,
        board_state,
        power_name,
        possible_orders,
        game_history,
        agent_goals,
        agent_relationships,
        agent_private_diary_str,
    );

    if (prompt.startsWith("Error:")) return prompt; // Error from prompt building

    const raw_response = await run_llm_and_log({
        client: this,
        prompt,
        log_file_path,
        power_name,
        phase: game_phase,
        response_type: 'plan_reply',
    });
    logger.debug(`[${this.model_name}] Raw LLM response for ${power_name} planning reply:\n${raw_response}`);
    return raw_response;
  }

  async get_conversation_reply(
    game: Game,
    board_state: any,
    power_name: string,
    possible_orders: PossibleOrders,
    game_history: GameHistory,
    game_phase: string,
    log_file_path: string,
    active_powers?: string[], // Currently unused in Python, but kept for signature consistency
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary_str?: string,
  ): Promise<Array<Record<string, string>>> {
    let raw_input_prompt = "";
    let raw_response = "";
    let success_status = "Failure: Initialized";
    let messages_to_return: Array<Record<string, string>> = [];

    try {
        raw_input_prompt = this.build_conversation_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
            agent_goals,
            agent_relationships,
            agent_private_diary_str,
        );

        if (raw_input_prompt.startsWith("Error:")) {
            throw new Error("Failed to build conversation prompt.");
        }

        logger.debug(`[${this.model_name}] Conversation prompt for ${power_name}:\n${raw_input_prompt.substring(0, 500)}...`);

        raw_response = await run_llm_and_log({
            client: this,
            prompt: raw_input_prompt,
            log_file_path,
            power_name,
            phase: game_phase,
            response_type: 'negotiation',
        });
        logger.debug(`[${this.model_name}] Raw LLM response for ${power_name}:\n${raw_response}`);

        const parsed_messages: Array<Record<string, string>> = [];
        let json_blocks: string[] = [];
        let json_decode_error_occurred = false;

        const double_brace_blocks = Array.from(raw_response.matchAll(/\{\{(.*?)\}\}/gs)).map(m => `{${m[1].trim()}}`);

        if (double_brace_blocks.length > 0) {
            json_blocks = double_brace_blocks;
        } else {
            const code_block_match = raw_response.match(/```json\s*([\s\S]*?)\s*```/s);
            if (code_block_match && code_block_match[1]) {
                const potential_json_content = code_block_match[1].trim();
                try {
                    const data = JSON.parse(potential_json_content);
                    if (Array.isArray(data)) {
                        json_blocks = data.filter(item => typeof item === 'object').map(item => JSON.stringify(item));
                    } else if (typeof data === 'object' && data !== null) {
                        json_blocks = [JSON.stringify(data)];
                    }
                } catch (e) {
                    // If parsing the whole block fails, try to find individual objects
                    json_blocks = Array.from(potential_json_content.matchAll(/\{[\s\S]*?\}/g)).map(m => m[0]);
                }
            } else {
                json_blocks = Array.from(raw_response.matchAll(/\{[\s\S]*?\}/g)).map(m => m[0]);
            }
        }

        if (json_blocks.length === 0) {
            logger.warn(`[${this.model_name}] No JSON message blocks found in response for ${power_name}. Raw response:\n${raw_response}`);
            success_status = "Success: No JSON blocks found";
        } else {
            for (let i = 0; i < json_blocks.length; i++) {
                const block = json_blocks[i];
                try {
                    let cleaned_block = block.trim();
                    cleaned_block = cleaned_block.replace(/,\s*([}\]])/g, '$1');

                    const parsed_message = JSON.parse(cleaned_block) as Record<string, string>;

                    if (parsed_message.message_type && parsed_message.content) {
                        if (parsed_message.message_type === "private" && !parsed_message.recipient) {
                            logger.warn(`[${this.model_name}] Private message missing recipient for ${power_name} in block ${i}. Skipping: ${cleaned_block}`);
                            continue;
                        }
                        parsed_messages.push(parsed_message);
                    } else {
                        logger.warn(`[${this.model_name}] Invalid message structure or missing keys in block ${i} for ${power_name}: ${cleaned_block}`);
                    }
                } catch (jde) {
                    try {
                        // Attempt to fix unescaped newlines (very basic fix)
                        const fixed_block = block.replace(/\n/g, '\\n');
                        const parsed_message_fixed = JSON.parse(fixed_block) as Record<string, string>;
                        if (parsed_message_fixed.message_type && parsed_message_fixed.content) {
                           if (parsed_message_fixed.message_type === "private" && !parsed_message_fixed.recipient) {
                                logger.warn(`[${this.model_name}] Private message missing recipient (after fix) for ${power_name} in block ${i}. Skipping: ${fixed_block}`);
                                continue;
                            }
                            parsed_messages.push(parsed_message_fixed);
                            logger.info(`[${this.model_name}] Successfully parsed JSON block ${i} for ${power_name} after fixing escape sequences`);
                        } else {
                             logger.warn(`[${this.model_name}] Invalid message structure (after fix) in block ${i} for ${power_name}: ${fixed_block}`);
                        }
                    } catch (jde2: any) {
                        json_decode_error_occurred = true;
                        logger.warn(`[${this.model_name}] Failed to decode JSON block ${i} for ${power_name} even after escape fixes. Error: ${jde2.message}. Block: ${block.substring(0,100)}`);
                    }
                }
            }

            if (parsed_messages.length > 0) {
                success_status = "Success: Messages extracted";
                messages_to_return = parsed_messages;
            } else if (json_decode_error_occurred) {
                success_status = "Failure: JSONDecodeError during block parsing";
            } else {
                success_status = "Success: No valid messages extracted from JSON blocks";
            }
        }
        logger.debug(`[${this.model_name}] Validated conversation replies for ${power_name}: ${JSON.stringify(messages_to_return)}`);

    } catch (e: any) {
        logger.error(`[${this.model_name}] Error in get_conversation_reply for ${power_name}: ${e.message}`, e);
        success_status = `Failure: Exception (${e.constructor.name})`;
    } finally {
        if (log_file_path) {
            log_llm_response({
                log_file_path,
                model_name: this.model_name,
                power_name,
                phase: game_phase,
                response_type: "negotiation_message",
                raw_input_prompt,
                raw_response,
                success: success_status,
            });
        }
    }
    return messages_to_return;
  }

  async get_plan(
    game: Game,
    board_state: any,
    power_name: string,
    game_history: GameHistory,
    log_file_path: string,
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary_str?: string,
  ): Promise<string> {
    logger.info(`Client generating strategic plan for ${power_name}...`);

    const planning_instructions = load_prompt("planning_instructions.txt");
    if (!planning_instructions) {
        logger.error("Could not load planning_instructions.txt! Cannot generate plan.");
        return "Error: Planning instructions not found.";
    }

    const possible_orders_for_context: PossibleOrders = {}; // Empty for high-level plan context

    const context_prompt_str = build_context_prompt({ // Using placeholder
        game,
        board_state,
        power_name,
        possible_orders: possible_orders_for_context,
        game_history,
        agent_goals,
        agent_relationships,
        agent_private_diary: agent_private_diary_str,
    });

    let full_prompt = `${context_prompt_str}\n\n${planning_instructions}`;
    if (this.system_prompt && this.system_prompt.trim().length > 0) { // Check if system_prompt is not null or empty
        full_prompt = `${this.system_prompt}\n\n${full_prompt}`;
    }

    let raw_plan_response = "";
    let success_status = "Failure: Initialized";
    let plan_to_return = `Error: Plan generation failed for ${power_name} (initial state)`;

    try {
        raw_plan_response = await run_llm_and_log({
            client: this,
            prompt: full_prompt,
            log_file_path,
            power_name,
            phase: game.current_short_phase,
            response_type: 'plan_generation',
        });
        logger.debug(`[${this.model_name}] Raw LLM response for ${power_name} plan generation:\n${raw_plan_response}`);
        plan_to_return = raw_plan_response.trim();
        success_status = "Success";
    } catch (e: any) {
        logger.error(`Failed to generate plan for ${power_name}: ${e.message}`, e);
        success_status = `Failure: Exception (${e.constructor.name})`;
        plan_to_return = `Error: Failed to generate plan for ${power_name} due to exception: ${e.message}`;
    } finally {
        if (log_file_path) {
            log_llm_response({
                log_file_path,
                model_name: this.model_name,
                power_name,
                phase: game.current_short_phase || "UnknownPhase",
                response_type: "plan_generation",
                raw_input_prompt: full_prompt,
                raw_response: raw_plan_response,
                success: success_status,
            });
        }
    }
    return plan_to_return;
  }
}

// Concrete Implementations

// Using 'any' for SDK types for now to simplify initial conversion.
// In a full conversion, install and use types from @openai/api, @anthropic-ai/sdk, @google/generative-ai
import { OpenAI as OpenAIClientSDK, AsyncOpenAI } from 'openai';
import { Anthropic as AnthropicSDK, AsyncAnthropic } from '@anthropic-ai/sdk'; // Corrected import
import * as genai from '@google/generative-ai';


export class OpenAIClient extends BaseModelClient {
  private client: AsyncOpenAI;

  constructor(model_name: string) {
    super(model_name);
    this.client = new AsyncOpenAI({ apiKey: process.env.OPENAI_API_KEY });
  }

  async generate_response(prompt: string): Promise<string> {
    try {
      const prompt_with_cta = `${prompt}\n\nPROVIDE YOUR RESPONSE BELOW:`;
      const response = await this.client.chat.completions.create({
        model: this.model_name,
        messages: [
          { role: "system", content: this.system_prompt || "" }, // Ensure system_prompt is not null
          { role: "user", content: prompt_with_cta },
        ],
      });
      if (!response || !response.choices || response.choices.length === 0 || !response.choices[0].message) {
        logger.warn(`[${this.model_name}] Empty or invalid result in generate_response. Returning empty.`);
        return "";
      }
      return response.choices[0].message.content?.trim() || "";
    } catch (e: any) {
      logger.error(`[${this.model_name}] Unexpected error in generate_response: ${e.message}`, e);
      return "";
    }
  }
}

export class ClaudeClient extends BaseModelClient {
  private client: AsyncAnthropic;

  constructor(model_name: string) {
    super(model_name);
    this.client = new AsyncAnthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  }

  async generate_response(prompt: string): Promise<string> {
    try {
      const response = await this.client.messages.create({
        model: this.model_name,
        max_tokens: 4000,
        system: this.system_prompt || undefined, // Pass undefined if system_prompt is null or empty
        messages: [{ role: "user", content: `${prompt}\n\nPROVIDE YOUR RESPONSE BELOW:` }],
      });
      if (!response.content || response.content.length === 0) {
        logger.warn(`[${this.model_name}] Empty content in Claude generate_response. Returning empty.`);
        return "";
      }
      return response.content[0].text.trim();
    } catch (e: any) {
      logger.error(`[${this.model_name}] Unexpected error in generate_response: ${e.message}`, e);
      return "";
    }
  }
}

export class GeminiClient extends BaseModelClient {
  private client: genai.GenerativeModel;

  constructor(model_name: string) {
    super(model_name);
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY environment variable is required");
    }
    const genAI = new genai.GoogleGenerativeAI(apiKey);
    this.client = genAI.getGenerativeModel({ model: model_name });
    logger.debug(`[${this.model_name}] Initialized Gemini client`);
  }

  async generate_response(prompt: string): Promise<string> {
    const full_prompt = `${this.system_prompt || ""}\n${prompt}\n\nPROVIDE YOUR RESPONSE BELOW:`;
    try {
      const result = await this.client.generateContent(full_prompt);
      const response = result.response; // Access the response part of GenerationResult
      if (!response || !response.text) { // Check response.text() if it's a function, or response.text if property
          let textContent = "";
          try {
            textContent = response.text(); // If text is a function
          } catch (e) {
             // If response.text is not a function, perhaps it's a property or missing.
             // This part might need adjustment based on actual SDK behavior for empty/error responses.
             logger.warn(`[${this.model_name}] Gemini response.text() method not available or failed. Checking candidates.`);
             if (response.candidates && response.candidates.length > 0 && response.candidates[0].content && response.candidates[0].content.parts.length > 0) {
                 textContent = response.candidates[0].content.parts.map(part => part.text).join("");
             }
          }

          if (!textContent.trim()) {
            logger.warn(`[${this.model_name}] Empty Gemini generate_response. Returning empty.`);
            return "";
          }
          return textContent.trim();
      }
      // If response.text was directly accessible (not a function)
      // This case might be redundant if response.text() is the primary way
      if (typeof response.text === 'function') { // Should have been caught by try/catch for text()
           const textContent = response.text();
            return textContent.trim();
      } else if (typeof (response as any).text === 'string') { // If .text is a string property
            return (response as any).text.trim();
      }
      // Fallback if structure is unexpected
      logger.warn(`[${this.model_name}] Unexpected Gemini response structure. Response: ${JSON.stringify(response)}`);
      return "";

    } catch (e: any) {
      logger.error(`[${this.model_name}] Error in Gemini generate_response: ${e.message}`, e);
      return "";
    }
  }
}

export class DeepSeekClient extends BaseModelClient {
  private client: AsyncOpenAI;

  constructor(model_name: string) {
    super(model_name);
    this.client = new AsyncOpenAI({
      apiKey: process.env.DEEPSEEK_API_KEY,
      baseURL: "https://api.deepseek.com/",
    });
  }

  async generate_response(prompt: string): Promise<string> {
    try {
      const prompt_with_cta = `${prompt}\n\nPROVIDE YOUR RESPONSE BELOW:`;
      const response = await this.client.chat.completions.create({
        model: this.model_name,
        messages: [
          { role: "system", content: this.system_prompt || "" },
          { role: "user", content: prompt_with_cta },
        ],
        stream: false,
      });
      logger.debug(`[${this.model_name}] Raw DeepSeek response:\n${JSON.stringify(response)}`);
      if (!response || !response.choices || response.choices.length === 0 || !response.choices[0].message) {
        logger.warn(`[${this.model_name}] No valid response in generate_response.`);
        return "";
      }
      const content = response.choices[0].message.content?.trim() || "";
      if (!content) {
        logger.warn(`[${this.model_name}] DeepSeek returned empty content.`);
        return "";
      }
      return content;
    } catch (e: any) {
      logger.error(`[${this.model_name}] Unexpected error in generate_response: ${e.message}`, e);
      return "";
    }
  }
}

export class OpenRouterClient extends BaseModelClient {
  private client: AsyncOpenAI;

  constructor(model_id: string = "openrouter/quasar-alpha") { // model_id to avoid conflict with class member
    let qualified_model_id = model_id;
    if (!qualified_model_id.startsWith("openrouter/") && !qualified_model_id.includes("/")) {
        qualified_model_id = `openrouter/${qualified_model_id}`;
    }
    // The Python code has: if model_name.startswith("openrouter-"): model_name = model_name.replace("openrouter-", "")
    // This seems to imply that the model_name passed to super() should be the short form,
    // but the actual model identifier for the API call should be the qualified one.
    // For OpenRouter, the model parameter in API calls is usually the full path e.g. "google/gemini-flash-1.5"
    // So, this.model_name should store the identifier used for API calls.
    // The original Python code: super().__init__(model_name) where model_name could be "google/gemini-flash-1.5"
    // Let's assume this.model_name should be the potentially fully qualified name for the API.
    super(qualified_model_id); // Pass the potentially modified model_id

    const apiKey = process.env.OPENROUTER_API_KEY;
    if (!apiKey) {
      throw new Error("OPENROUTER_API_KEY environment variable is required");
    }
    this.client = new AsyncOpenAI({
      baseURL: "https://openrouter.ai/api/v1",
      apiKey: apiKey,
    });
    logger.debug(`[${this.model_name}] Initialized OpenRouter client for model ${this.model_name}`);
  }

  async generate_response(prompt: string): Promise<string> {
    try {
      const prompt_with_cta = `${prompt}\n\nPROVIDE YOUR RESPONSE BELOW:`;
      const response = await this.client.chat.completions.create({
        model: this.model_name, // Use the model_name stored in the instance
        messages: [
          { role: "system", content: this.system_prompt || "" },
          { role: "user", content: prompt_with_cta },
        ],
        max_tokens: 4000,
      });
      if (!response.choices || response.choices.length === 0 || !response.choices[0].message) {
        logger.warn(`[${this.model_name}] OpenRouter returned no choices`);
        return "";
      }
      const content = response.choices[0].message.content?.trim() || "";
      if (!content) {
        logger.warn(`[${this.model_name}] OpenRouter returned empty content`);
        return "";
      }
      return content;
    } catch (e: any) {
      const error_msg = String(e);
      if (error_msg.includes("429") || error_msg.toLowerCase().includes("rate")) {
        logger.warn(`[${this.model_name}] OpenRouter rate limit error: ${e.message}`);
        throw e;
      } else if (error_msg.toLowerCase().includes("provider") && error_msg.toLowerCase().includes("error")) {
        logger.error(`[${this.model_name}] OpenRouter provider error: ${e.message}`);
        throw e;
      } else {
        logger.error(`[${this.model_name}] Error in OpenRouter generate_response: ${e.message}`, e);
        return "";
      }
    }
  }
}

// Factory Function
export function load_model_client(model_id: string): BaseModelClient {
  const lower_id = model_id.toLowerCase();
  if (lower_id.startsWith("openrouter/") || lower_id.includes("/") && !lower_id.startsWith("deepseek")) { // Heuristic for OpenRouter
    return new OpenRouterClient(model_id); // OpenRouterClient handles its own prefixing
  } else if (lower_id.includes("claude")) {
    return new ClaudeClient(model_id);
  } else if (lower_id.includes("gemini")) {
    return new GeminiClient(model_id);
  } else if (lower_id.includes("deepseek")) {
    return new DeepSeekClient(model_id);
  } else {
    // Default to OpenAI for gpt-4o, o3-mini etc.
    return new OpenAIClient(model_id);
  }
}

// Utility function (get_visible_messages_for_power)
interface Message {
    sender: string;
    recipient: string;
    // other message properties
}

export function get_visible_messages_for_power(conversation_messages: Message[], power_name: string): Message[] {
    return conversation_messages.filter(msg =>
        msg.recipient === "ALL" ||
        msg.recipient === "GLOBAL" ||
        msg.sender === power_name ||
        msg.recipient === power_name
    );
}

// Example Usage (conceptual, not directly runnable without game loop)
/*
async function example_game_loop(game: Game) { // Assuming Game type is defined
    const active_powers = Object.entries(game.powers) // Assuming game.powers is a Record<string, PowerObject>
        .filter(([_, p_obj]: [string, any]) => !p_obj.is_eliminated())
        .map(([p_name, _]) => p_name);

    // const power_model_mapping = assign_models_to_powers(); // This function needs to be defined

    for (const power_name of active_powers) {
        // const model_id = power_model_mapping.get(power_name) || "o3-mini";
        const client = load_model_client("o3-mini"); // Example model

        const possible_orders = game.get_all_possible_orders();
        const board_state = game.get_state();

        // Example: Fetch agent instance and diary
        // const agent = agents_dict[power_name];
        // const formatted_diary = agent.format_private_diary_for_prompt();

        // const orders = await client.get_orders(
        //     game,
        //     board_state,
        //     power_name,
        //     possible_orders,
        //     game_history, // Needs game_history instance
        //     null, // model_error_stats
        //     "path/to/log.csv", // log_file_path
        //     game.current_short_phase,
        //     agent_goals, // agent.goals
        //     agent_relationships, // agent.relationships
        //     formatted_diary
        // );
        // game.set_orders(power_name, orders);
    }
    // game.process();
}
*/
