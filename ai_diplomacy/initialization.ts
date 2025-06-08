import * as dotenv from 'dotenv';

// Assuming placeholder interfaces and utility functions from other .ts files
// These would be properly imported from their respective files in a complete conversion.

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

// Placeholders from agent.ts (or should be from a shared types file)
interface DiplomacyAgent {
  power_name: string;
  client: any; // Should be BaseModelClient from clients.ts
  goals: string[];
  relationships: Record<string, string>;
  format_private_diary_for_prompt(): string;
  add_journal_entry(entry: string): void;
  _extract_json_from_text(text: string): any; // Assuming this method exists on the TS agent
}

interface Game {
  current_short_phase: string;
  get_state(): any;
  get_current_phase(): string;
  get_all_possible_orders(): Record<string, string[]>;
  powers: string[];
}

interface GameHistory {
  // Define necessary GameHistory properties/methods if needed by build_context_prompt
  // For now, keeping it minimal as build_context_prompt is a placeholder.
  phases: Array<{ name: string }>;
}

// Constants (should be imported from a shared constants file or agent.ts)
const ALL_POWERS: ReadonlySet<string> = new Set([
  "AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY",
]);
const ALLOWED_RELATIONSHIPS: string[] = ["Enemy", "Unfriendly", "Neutral", "Friendly", "Ally"];

// Placeholder for utility functions (assuming they exist in a utils.ts or similar)
const run_llm_and_log = async (args: {
  client: any; // Should be BaseModelClient
  prompt: string;
  log_file_path: string;
  power_name: string;
  phase: string;
  response_type: string;
}): Promise<string> => {
  logger.warn(`run_llm_and_log called for ${args.power_name} (${args.response_type}). Placeholder.`);
  // Simulate LLM call
  if (args.prompt.includes("initial_goals") && args.prompt.includes("initial_relationships")) {
    return JSON.stringify({
        initial_goals: ["Test Goal 1 from LLM", "Test Goal 2 from LLM"],
        initial_relationships: { "FRANCE": "Ally", "GERMANY": "Enemy" }
    });
  }
  return "{}"; // Default empty JSON
};

const log_llm_response = (args: {
  log_file_path: string;
  model_name: string;
  power_name: string;
  phase: string;
  response_type: string;
  raw_input_prompt: string;
  raw_response: string;
  success: string;
}) => {
  logger.info(`[log_llm_response] Logging for ${args.power_name}, Type: ${args.response_type}, Success: ${args.success}`);
};

const build_context_prompt = (args: any): string => {
  logger.warn("build_context_prompt called. Placeholder implementation.");
  return `Placeholder context for ${args.power_name}`;
};


export async function initialize_agent_state_ext(
    agent: DiplomacyAgent,
    game: Game,
    game_history: GameHistory,
    log_file_path: string
): Promise<void> {
    const power_name = agent.power_name;
    logger.info(`[${power_name}] Initializing agent state using LLM (external function)...`);
    const current_phase = game ? game.get_current_phase() : "UnknownPhase";

    let full_prompt = "";
    let response = "";
    let success_status = "Failure: Initialized";

    try {
        const allowed_labels_str = ALLOWED_RELATIONSHIPS.join(", ");
        const initial_prompt = `You are the agent for ${power_name} in a game of Diplomacy at the very start (Spring 1901). ` +
                         `Analyze the initial board position and suggest 2-3 strategic high-level goals for the early game. ` +
                         `Consider your power's strengths, weaknesses, and neighbors. ` +
                         `Also, provide an initial assessment of relationships with other powers. ` +
                         `IMPORTANT: For each relationship, you MUST use exactly one of the following labels: ${allowed_labels_str}. ` +
                         `Format your response as a JSON object with two keys: 'initial_goals' (a list of strings) and 'initial_relationships' (a dictionary mapping power names to one of the allowed relationship strings).`;

        const board_state = game ? game.get_state() : {};
        const possible_orders = game ? game.get_all_possible_orders() : {};

        logger.debug(`[${power_name}] Preparing context for initial state. Board state type: ${typeof board_state}, possible_orders type: ${typeof possible_orders}, game_history type: ${typeof game_history}`);

        const formatted_diary = agent.format_private_diary_for_prompt();

        const context = build_context_prompt({
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
            agent_goals: undefined, // Explicitly undefined for initialization
            agent_relationships: undefined, // Explicitly undefined for initialization
            agent_private_diary: formatted_diary,
        });
        full_prompt = `${initial_prompt}\n\n${context}`;

        response = await run_llm_and_log({
            client: agent.client,
            prompt: full_prompt,
            log_file_path,
            power_name,
            phase: current_phase,
            response_type: 'initialization',
        });
        logger.debug(`[${power_name}] LLM response for initial state: ${response.substring(0,300)}...`);

        let parsed_successfully = false;
        let update_data: any = {};
        try {
            update_data = agent._extract_json_from_text(response); // Assumes agent has this method
            logger.debug(`[${power_name}] Successfully parsed JSON: ${JSON.stringify(update_data)}`);
            parsed_successfully = true;
        } catch (e: any) { // Assuming _extract_json_from_text might throw if it cannot parse anything
            logger.error(`[${power_name}] JSON extraction failed: ${e.message}. Response snippet: ${response.substring(0,300)}...`);
            success_status = "Failure: JSONExtractionError"; // More specific than JSONDecodeError if _extract handles multiple types
            update_data = {};
            parsed_successfully = false;
        }

        if (parsed_successfully) {
            if (typeof update_data === 'string') {
                logger.error(`[${power_name}] _extract_json_from_text returned a string. String: ${update_data.substring(0,300)}...`);
                update_data = {};
                parsed_successfully = false;
                success_status = "Failure: ParsedAsStr";
            } else if (typeof update_data !== 'object' || update_data === null) {
                logger.error(`[${power_name}] _extract_json_from_text returned non-object type (${typeof update_data}). Data: ${String(update_data).substring(0,300)}`);
                update_data = {};
                parsed_successfully = false;
                success_status = "Failure: NotAnObject";
            }
        }

        let initial_goals_applied = false;
        let initial_relationships_applied = false;

        if (parsed_successfully && typeof update_data === 'object' && update_data !== null) {
            const initial_goals = update_data.initial_goals || update_data.goals;
            const initial_relationships_data = update_data.initial_relationships || update_data.relationships;

            if (Array.isArray(initial_goals) && initial_goals.length > 0) {
                agent.goals = initial_goals.filter(g => typeof g === 'string'); // Ensure all goals are strings
                agent.add_journal_entry(`[${current_phase}] Initial Goals Set by LLM: ${JSON.stringify(agent.goals)}`);
                logger.info(`[${power_name}] Goals updated from LLM: ${JSON.stringify(agent.goals)}`);
                initial_goals_applied = true;
            } else {
                logger.warn(`[${power_name}] LLM did not provide valid 'initial_goals' list (got: ${JSON.stringify(initial_goals)}).`);
            }

            if (typeof initial_relationships_data === 'object' && initial_relationships_data !== null && Object.keys(initial_relationships_data).length > 0) {
                const valid_relationships: Record<string, string> = {};
                for (const [p_key, r_val] of Object.entries(initial_relationships_data)) {
                    const p_upper = String(p_key).toUpperCase();
                    const r_title = typeof r_val === 'string' ? (r_val.charAt(0).toUpperCase() + r_val.slice(1).toLowerCase()) : String(r_val);
                    if (ALL_POWERS.has(p_upper) && p_upper !== power_name) {
                        if (ALLOWED_RELATIONSHIPS.includes(r_title)) {
                            valid_relationships[p_upper] = r_title;
                        } else {
                            logger.warn(`[${power_name}] Invalid relationship label '${r_val}' for ${p_upper} from LLM. Defaulting to Neutral.`);
                            valid_relationships[p_upper] = "Neutral";
                        }
                    }
                }
                if (Object.keys(valid_relationships).length > 0) {
                    agent.relationships = valid_relationships;
                    agent.add_journal_entry(`[${current_phase}] Initial Relationships Set by LLM: ${JSON.stringify(agent.relationships)}`);
                    logger.info(`[${power_name}] Relationships updated from LLM: ${JSON.stringify(agent.relationships)}`);
                    initial_relationships_applied = true;
                } else {
                    logger.warn(`[${power_name}] No valid relationships found in LLM response after filtering.`);
                }
            } else {
                 logger.warn(`[${power_name}] LLM did not provide valid 'initial_relationships' object (got: ${JSON.stringify(initial_relationships_data)}).`);
            }

            if (initial_goals_applied || initial_relationships_applied) {
                success_status = "Success: Applied LLM data";
            } else if (parsed_successfully) {
                success_status = "Success: Parsed but no data applied";
            }
        }

        if (!initial_goals_applied) {
            if (agent.goals.length === 0) {
                agent.goals = ["Survive and expand", "Form beneficial alliances", "Secure key territories"];
                agent.add_journal_entry(`[${current_phase}] Set default initial goals as LLM provided none or parse failed.`);
                logger.info(`[${power_name}] Default goals set.`);
            }
        }

        if (!initial_relationships_applied) {
            let is_default_relationships = true;
            if (agent.relationships && Object.keys(agent.relationships).length > 0) {
                for (const p of ALL_POWERS) {
                    if (p !== power_name && agent.relationships[p] !== "Neutral") {
                        is_default_relationships = false;
                        break;
                    }
                }
            }
            if (is_default_relationships) {
                agent.relationships = {};
                ALL_POWERS.forEach(p => {
                    if (p !== power_name) agent.relationships[p] = "Neutral";
                });
                agent.add_journal_entry(`[${current_phase}] Set default neutral relationships as LLM provided none valid or parse failed.`);
                logger.info(`[${power_name}] Default neutral relationships set.`);
            }
        }

    } catch (e: any) {
        logger.error(`[${power_name}] Error during external agent state initialization: ${e.message}`, e);
        success_status = `Failure: Exception (${e.constructor.name})`;
        if (agent.goals.length === 0) {
            agent.goals = ["Survive and expand", "Form beneficial alliances", "Secure key territories"];
            logger.info(`[${power_name}] Set fallback goals after top-level error: ${JSON.stringify(agent.goals)}`);
        }
        if (!agent.relationships || Object.values(agent.relationships).every(r => r === "Neutral")) {
            agent.relationships = {};
            ALL_POWERS.forEach(p => {
                if (p !== power_name) agent.relationships[p] = "Neutral";
            });
            logger.info(`[${power_name}] Set fallback neutral relationships after top-level error: ${JSON.stringify(agent.relationships)}`);
        }
    } finally {
        if (log_file_path) {
            log_llm_response({
                log_file_path,
                model_name: agent?.client?.model_name ?? "UnknownModel",
                power_name,
                phase: current_phase,
                response_type: "initial_state_setup",
                raw_input_prompt: full_prompt,
                raw_response: response,
                success: success_status,
            });
        }
    }
    logger.info(`[${power_name}] Post-initialization state: Goals=${JSON.stringify(agent.goals)}, Relationships=${JSON.stringify(agent.relationships)}`);
}
