// Assuming BaseModelClient is importable from clients.ts in the same directory
// Placeholder for now
interface BaseModelClient {
  set_system_prompt(prompt: string): void;
  get_plan(game: Game, board_state: any, power_name: string, game_history: GameHistory): Promise<string>;
  model_name: string; // Added based on usage in generate_order_diary_entry
}

// Placeholder for Game interface
interface Game {
  current_short_phase: string;
  get_state(): any; // Replace 'any' with a more specific type later
  get_current_phase(): string;
  get_all_possible_orders(): any; // Replace 'any' with a more specific type later
  powers: string[];
}

// Placeholder for GameHistory interface
interface GameHistory {
  get_messages_this_round(power_name: string, current_phase_name: string): string;
  get_ignored_messages_by_power(power_name: string): Record<string, Array<{ phase: string; content: string }>>;
  phases: Array<{ name: string }>; // Assuming phase object has a 'name' attribute
  get_messages_by_phase(phase_name: string): Array<{ sender: string; recipient: string; content: string }>;
}

// Placeholder for load_model_client and run_llm_and_log, log_llm_response, load_prompt, build_context_prompt
// These would typically be imported from other TypeScript files.
const load_model_client = (clientName: string): BaseModelClient | null => {
  console.warn(`load_model_client called with ${clientName}. Returning null as placeholder.`);
  return null;
};

const run_llm_and_log = async (args: {
  client: BaseModelClient;
  prompt: string;
  log_file_path: string;
  power_name: string;
  phase: string;
  response_type: string;
}): Promise<string> => {
  console.warn("run_llm_and_log called. Returning empty string as placeholder.");
  return "";
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
  console.warn("log_llm_response called. Placeholder implementation.");
};

const load_prompt = (filepath: string): string | null => {
  console.warn(`load_prompt called with ${filepath}. Returning null as placeholder.`);
  return null;
};

const build_context_prompt = (args: {
  game: Game;
  board_state: any;
  power_name: string;
  possible_orders: any;
  game_history: GameHistory;
  agent_goals: string[];
  agent_relationships: Record<string, string>;
  agent_private_diary: string;
}): string => {
  console.warn("build_context_prompt called. Returning empty string as placeholder.");
  return "";
};


import json5 from 'json5';
// import { loads as jsonRepairLoads } from 'json-repair'; // Would be imported if available

// Using console.log for logger for now. A proper logging library should be used in a real application.
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string) => console.error(message),
};

// == Best Practice: Define constants at module level ==
const ALL_POWERS: ReadonlySet<string> = new Set([
  "AUSTRIA",
  "ENGLAND",
  "FRANCE",
  "GERMANY",
  "ITALY",
  "RUSSIA",
  "TURKEY",
]);
const ALLOWED_RELATIONSHIPS: string[] = ["Enemy", "Unfriendly", "Neutral", "Friendly", "Ally"];

// == New: Helper function to load prompt files reliably ==
// Note: In Node.js, file system operations are typically asynchronous.
// For simplicity, using a synchronous placeholder or assuming it's handled elsewhere.
// In a real Node.js app, use 'fs.readFileSync' or async file operations.
const _load_prompt_file = (filename: string): string | null => {
  logger.warn(`_load_prompt_file called for ${filename}. This is a placeholder.`);
  // In a real scenario, you would use something like:
  // import * as fs from 'fs';
  // import * as path from 'path';
  // const currentDir = __dirname; // or import.meta.url for ES modules
  // const promptsDir = path.join(currentDir, 'prompts');
  // const filepath = path.join(promptsDir, filename);
  // try {
  //   return fs.readFileSync(filepath, 'utf-8');
  // } catch (error) {
  //   logger.error(`Prompt file not found: ${filepath}`);
  //   return null;
  // }
  return null; // Placeholder
};

interface DiplomacyAgentArgs {
  power_name: string;
  client: BaseModelClient;
  initial_goals?: string[];
  initial_relationships?: Record<string, string>;
}

class DiplomacyAgent {
  public power_name: string;
  public client: BaseModelClient;
  public goals: string[];
  public relationships: Record<string, string>;
  public private_journal: string[];
  public private_diary: string[]; // New private diary

  constructor({
    power_name,
    client,
    initial_goals,
    initial_relationships,
  }: DiplomacyAgentArgs) {
    if (!ALL_POWERS.has(power_name)) {
      throw new Error(
        `Invalid power name: ${power_name}. Must be one of ${Array.from(ALL_POWERS).join(", ")}`
      );
    }

    this.power_name = power_name;
    this.client = client;
    this.goals = initial_goals ?? [];

    if (initial_relationships === undefined) {
      this.relationships = {};
      ALL_POWERS.forEach(p => {
        if (p !== this.power_name) {
          this.relationships[p] = "Neutral";
        }
      });
    } else {
      this.relationships = initial_relationships;
    }

    this.private_journal = [];
    this.private_diary = [];

    // --- Load and set the appropriate system prompt ---
    // In Node.js, path resolution needs to be handled carefully.
    // Assuming prompts are in a 'prompts' directory relative to this file.
    // This part needs to be adapted to how files are served/accessed in TypeScript (e.g., using fs module).
    const power_prompt_filename = `prompts/${power_name.toLowerCase()}_system_prompt.txt`;
    const default_prompt_filename = `prompts/system_prompt.txt`;

    let system_prompt_content = load_prompt(power_prompt_filename);

    if (!system_prompt_content) {
      logger.warn(
        `Power-specific prompt '${power_prompt_filename}' not found or empty. Loading default system prompt.`
      );
      system_prompt_content = load_prompt(default_prompt_filename);
    } else {
      logger.info(`Loaded power-specific system prompt for ${power_name}.`);
    }
    // ----------------------------------------------------

    if (system_prompt_content) {
      this.client.set_system_prompt(system_prompt_content);
    } else {
      logger.error(
        `Could not load default system prompt either! Agent ${power_name} may not function correctly.`
      );
    }
    logger.info(
      `Initialized DiplomacyAgent for ${this.power_name} with goals: ${JSON.stringify(this.goals)}`
    );
    this.add_journal_entry(`Agent initialized. Initial Goals: ${JSON.stringify(this.goals)}`);
  }

  // Method stubs to be implemented later
  private _clean_json_text(text: string): string {
    if (!text) {
        return text;
    }

    // Remove trailing commas
    text = text.replace(/,\s*}/g, '}');
    text = text.replace(/,\s*]/g, ']');

    // Fix newlines before JSON keys
    text = text.replace(/\n\s+"(\w+)"\s*:/g, '"$1":');

    // Replace single quotes with double quotes for keys
    text = text.replace(/'(\w+)'\s*:/g, '"$1":');

    // Remove comments (if any)
    text = text.replace(/\/\/.*$/gm, '');
    text = text.replace(/\/\*.*?\*\//gs, '');

    // Fix unescaped quotes in values (basic attempt)
    // This is risky but sometimes helps with simple cases
    text = text.replace(/:\s*"([^"]*)"([^",}\]])"/g, ': "$1$2"');

    // Remove any BOM or zero-width spaces
    text = text.replace(/\ufeff/g, '').replace(/\u200b/g, '');

    return text.trim();
  }

  private _extract_json_from_text(text: string): any {
    if (!text || !text.trim()) {
        logger.warn(`[${this.power_name}] Empty text provided to JSON extractor`);
        return {};
    }

    let original_text = text;

    // Preprocessing: Normalize common formatting issues
    text = text.replace(/\n\s+"(\w+)"\s*:/g, '"$1":'); // Remove newlines before keys
    const problematic_patterns_list: string[] = [
        'negotiation_summary', 'relationship_updates', 'updated_relationships',
        'order_summary', 'goals', 'relationships', 'intent'
    ];
    for (const pattern_item of problematic_patterns_list) {
        text = text.replace(new RegExp(`\\n\\s*"${pattern_item}"`, 'g'), `"${pattern_item}"`);
    }

    const patterns: RegExp[] = [
        /```\s*\{\{\s*(.*?)\s*\}\}\s*```/s,
        /```(?:json)?\s*\n(.*?)\n\s*```/s,
        /PARSABLE OUTPUT:\s*(\{.*?\})/s,
        /JSON:\s*(\{.*?\})/s,
        /(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})/s,
        /`(\{.*?\})`/s,
    ];

    for (let pattern_idx = 0; pattern_idx < patterns.length; pattern_idx++) {
        const pattern = patterns[pattern_idx];
        // Using matchAll to find all occurrences
        const matches = Array.from(text.matchAll(pattern));

        if (matches.length > 0) {
            for (let match_idx = 0; match_idx < matches.length; match_idx++) {
                const match_array = matches[match_idx];
                // The actual captured group is usually at index 1
                const json_text = match_array[1] ? match_array[1].trim() : match_array[0].trim();


                // Attempt 1: Standard JSON after basic cleaning
                try {
                    const cleaned = this._clean_json_text(json_text);
                    const result = JSON.parse(cleaned);
                    logger.debug(`[${this.power_name}] Successfully parsed JSON with pattern ${pattern_idx}, match ${match_idx}`);
                    return result;
                } catch (e: any) {
                    logger.debug(`[${this.power_name}] Standard JSON parse failed: ${e.message}`);

                    // Attempt 1.5: Try surgical cleaning
                    try {
                        let cleaned_match_candidate = json_text;
                        cleaned_match_candidate = cleaned_match_candidate.replace(/\s*([A-Z][\w\s,]*?\.(?:\s+[A-Z][\w\s,]*?\.)*)\s*(?=[,\}\]])/g, '');
                        cleaned_match_candidate = cleaned_match_candidate.replace(/\s*([A-Z][\w\s,]*?\.(?:\s+[A-Z][\w\s,]*?\.)*)\s*(?=\s*\}\s*$)/g, '');
                        cleaned_match_candidate = cleaned_match_candidate.replace(/\n\s+"(\w+)"\s*:/g, '"$1":');
                        cleaned_match_candidate = cleaned_match_candidate.replace(/,\s*}/g, '}');
                        for (const p_item of problematic_patterns_list) {
                            cleaned_match_candidate = cleaned_match_candidate.replace(new RegExp(`\\n  "${p_item}"`, 'g'), `"${p_item}"`);
                        }
                        cleaned_match_candidate = cleaned_match_candidate.replace(/'(\w+)'\s*:/g, '"$1":');

                        if (cleaned_match_candidate !== json_text) {
                            logger.debug(`[${this.power_name}] Surgical cleaning applied. Attempting to parse modified JSON.`);
                            const result = JSON.parse(cleaned_match_candidate);
                            return result;
                        }
                    } catch (e_surgical: any) {
                        logger.debug(`[${this.power_name}] Surgical cleaning didn't work: ${e_surgical.message}`);
                    }
                }

                // Attempt 2: json5 (more forgiving)
                try {
                    const result = json5.parse(json_text);
                    logger.debug(`[${this.power_name}] Successfully parsed with json5`);
                    return result;
                } catch (e: any) {
                    logger.debug(`[${this.power_name}] json5 parse failed: ${e.message}`);
                }

                // Attempt 3: json-repair (if it were available)
                // try {
                //   const result = jsonRepairLoads(json_text);
                //   logger.debug(`[${this.power_name}] Successfully parsed with json-repair`);
                //   return result;
                // } catch (e: any) {
                //   logger.debug(`[${this.power_name}] json-repair failed: ${e.message}`);
                // }
            }
        }
    }

    // Fallback: Try to find ANY JSON-like structure
    try {
        const start = text.indexOf('{');
        const end = text.lastIndexOf('}') + 1;
        if (start !== -1 && end > start) {
            const potential_json = text.substring(start, end);

            for (const { parser_name, parser_func } of [
                { parser_name: "json", parser_func: JSON.parse },
                { parser_name: "json5", parser_func: json5.parse },
                // { parser_name: "json_repair", parser_func: jsonRepairLoads } // If available
            ]) {
                try {
                    const cleaned = parser_name === "json" ? this._clean_json_text(potential_json) : potential_json;
                    const result = parser_func(cleaned);
                    logger.debug(`[${this.power_name}] Fallback parse succeeded with ${parser_name}`);
                    return result;
                } catch (e: any) {
                    logger.debug(`[${this.power_name}] Fallback ${parser_name} failed: ${e.message}`);
                }
            }

            try {
                let cleaned_text = potential_json.replace(/[^{}[\]"',:.A-Za-z0-9\s_-]/g, ''); // Simplified regex
                cleaned_text = cleaned_text.replace(/'([^']*)':/g, '"$1":');
                cleaned_text = cleaned_text.replace(/:\s*'([^']*)'/g, ': "$1"');

                const result = JSON.parse(cleaned_text);
                logger.debug(`[${this.power_name}] Aggressive cleaning worked`);
                return result;
            } catch (e: any) {
                // Ignore error
            }
        }
    } catch (e: any) {
        logger.debug(`[${this.power_name}] Fallback extraction failed: ${e.message}`);
    }

    // Last resort: Try json5 on the entire text
    try {
        const result = json5.parse(text);
        logger.warn(`[${this.power_name}] Last resort json5 succeeded on entire text`);
        return result;
    } catch (e: any) {
        // logger.error(`[${this.power_name}] All JSON extraction attempts failed. Original text: ${original_text.substring(0,500)}...`);
        // Fallback to trying json-repair on the entire text if it were available
        // try {
        //   const result = jsonRepairLoads(text);
        //   logger.warn(`[${this.power_name}] Last resort json-repair succeeded on entire text`);
        //   return result;
        // } catch (eRepair: any) {
        //   logger.error(`[${this.power_name}] All JSON extraction attempts failed (including last resort json-repair). Original text: ${original_text.substring(0,500)}...`);
        //   return {};
        // }
         logger.error(`[${this.power_name}] All JSON extraction attempts failed. Original text: ${original_text.substring(0,500)}...`);
         return {};
    }
  }

  public add_journal_entry(entry: string): void {
    if (typeof entry !== 'string') {
        entry = String(entry);
    }
    this.private_journal.push(entry);
    logger.debug(`[${this.power_name} Journal]: ${entry}`);
  }

  public add_diary_entry(entry: string, phase: string): void {
    if (typeof entry !== 'string') {
        entry = String(entry);
    }
    const formatted_entry = `[${phase}] ${entry}`;
    this.private_diary.push(formatted_entry);
    logger.info(`[${this.power_name}] DIARY ENTRY ADDED for ${phase}. Total entries: ${this.private_diary.length}. New entry: ${entry.substring(0,100)}...`);
  }

  public format_private_diary_for_prompt(max_entries: number = 40): string {
    logger.info(`[${this.power_name}] Formatting diary for prompt. Total entries: ${this.private_diary.length}`);
    if (this.private_diary.length === 0) {
        logger.warn(`[${this.power_name}] No diary entries found when formatting for prompt`);
        return "(No diary entries yet)";
    }
    const recent_entries = this.private_diary.slice(-max_entries);
    const formatted_diary = recent_entries.join("\n");
    logger.info(`[${this.power_name}] Formatted ${recent_entries.length} diary entries for prompt. Preview: ${formatted_diary.substring(0,200)}...`);
    return formatted_diary;
  }

  public async consolidate_year_diary_entries(year: string, game: Game, log_file_path: string): Promise<void> {
    logger.info(`[${this.power_name}] CONSOLIDATION CALLED for year ${year}`);
    logger.info(`[${this.power_name}] Current diary has ${this.private_diary.length} total entries`);

    if (this.private_diary.length > 0) {
        logger.info(`[${this.power_name}] Sample diary entries:`);
        this.private_diary.slice(0, 3).forEach((entry, i) => {
            logger.info(`[${this.power_name}]   Entry ${i}: ${entry.substring(0, 100)}...`);
        });
    }

    const year_entries: string[] = [];
    const patterns_to_check = [`[S${year}`, `[F${year}`, `[W${year}`];
    logger.info(`[${this.power_name}] Looking for entries matching patterns: ${patterns_to_check}`);

    this.private_diary.forEach((entry, i) => {
        for (const pattern of patterns_to_check) {
            if (entry.includes(pattern)) {
                year_entries.push(entry);
                logger.info(`[${this.power_name}] Found matching entry ${i} with pattern '${pattern}': ${entry.substring(0, 50)}...`);
                break;
            }
        }
    });

    if (year_entries.length === 0) {
        logger.info(`[${this.power_name}] No diary entries found for year ${year} using patterns: ${patterns_to_check}`);
        return;
    }

    logger.info(`[${this.power_name}] Found ${year_entries.length} entries to consolidate for year ${year}`);

    const prompt_template = _load_prompt_file('diary_consolidation_prompt.txt');
    if (!prompt_template) {
        logger.error(`[${this.power_name}] Could not load diary_consolidation_prompt.txt`);
        return;
    }

    const year_diary_text = year_entries.join("\n\n");

    const prompt = prompt_template
        .replace('{power_name}', this.power_name)
        .replace('{year}', year)
        .replace('{year_diary_entries}', year_diary_text);

    let raw_response = "";
    let success_status = "FALSE";
    let consolidation_client: BaseModelClient | null = null;

    try {
        consolidation_client = load_model_client("openrouter-google/gemini-2.5-flash-preview");
        if (!consolidation_client) {
            consolidation_client = this.client;
            logger.warn(`[${this.power_name}] Using agent's own model for consolidation instead of Gemini Flash`);
        }

        raw_response = await run_llm_and_log({
            client: consolidation_client,
            prompt: prompt,
            log_file_path: log_file_path,
            power_name: this.power_name,
            phase: game.current_short_phase,
            response_type: 'diary_consolidation',
        });

        if (raw_response && raw_response.trim()) {
            const consolidated_entry = raw_response.trim();

            const consolidated_entries: string[] = [];
            const regular_entries: string[] = [];

            this.private_diary.forEach(entry => {
                if (entry.startsWith("[CONSOLIDATED")) {
                    consolidated_entries.push(entry);
                } else {
                    let should_keep = true;
                    for (const pattern of patterns_to_check) {
                        if (entry.includes(pattern)) {
                            should_keep = false;
                            break;
                        }
                    }
                    if (should_keep) {
                        regular_entries.push(entry);
                    }
                }
            });

            const consolidated_summary = `[CONSOLIDATED ${year}] ${consolidated_entry}`;
            consolidated_entries.push(consolidated_summary);

            // Sort consolidated entries by year (ascending)
            consolidated_entries.sort((a, b) => {
                const yearA = a.substring(14, 18);
                const yearB = b.substring(14, 18);
                return yearA.localeCompare(yearB);
            });

            this.private_diary = [...consolidated_entries, ...regular_entries];
            success_status = "TRUE";
            logger.info(`[${this.power_name}] Successfully consolidated ${year_entries.length} entries from ${year} into 1 summary`);
            logger.info(`[${this.power_name}] New diary structure - Total entries: ${this.private_diary.length}, Consolidated: ${consolidated_entries.length}, Regular: ${regular_entries.length}`);
            logger.debug(`[${this.power_name}] Diary order preview:`);
            this.private_diary.slice(0, 5).forEach((entry, i) => {
                logger.debug(`[${this.power_name}]   Entry ${i}: ${entry.substring(0, 50)}...`);
            });
        } else {
            logger.warn(`[${this.power_name}] Empty response from consolidation LLM`);
            success_status = "FALSE: Empty response";
        }

    } catch (e: any) {
        logger.error(`[${this.power_name}] Error consolidating diary entries: ${e.message}`, e);
        success_status = `FALSE: ${e.constructor.name}`;
    } finally {
        if (log_file_path) {
            log_llm_response({
                log_file_path: log_file_path,
                model_name: consolidation_client?.model_name ?? this.client.model_name,
                power_name: this.power_name,
                phase: game.current_short_phase,
                response_type: 'diary_consolidation',
                raw_input_prompt: prompt,
                raw_response: raw_response,
                success: success_status
            });
        }
    }
  }

  public async generate_negotiation_diary_entry(game: Game, game_history: GameHistory, log_file_path: string): Promise<void> {
    logger.info(`[${this.power_name}] Generating negotiation diary entry for ${game.current_short_phase}...` );

    let full_prompt = "";
    let raw_response = "";
    let success_status = "Failure: Initialized";

    try {
        let prompt_template_content = _load_prompt_file('negotiation_diary_prompt.txt');
        if (!prompt_template_content) {
            logger.error(`[${this.power_name}] Could not load negotiation_diary_prompt.txt. Skipping diary entry.`);
            success_status = "Failure: Prompt file not loaded";
            // Ensure logging happens even on early exit by calling log_llm_response in finally
            return; // Logged in finally
        }

        const board_state_dict = game.get_state();
        const board_state_str = `Units: ${JSON.stringify(board_state_dict.units || {})}, Centers: ${JSON.stringify(board_state_dict.centers || {})}`;

        let messages_this_round = game_history.get_messages_this_round(
            this.power_name,
            game.current_short_phase
        );
        if (!messages_this_round.trim() || messages_this_round.startsWith("\n(No messages")) {
            messages_this_round = "(No messages involving your power this round that require deep reflection for diary. Focus on overall situation.)";
        }

        const current_relationships_str = JSON.stringify(this.relationships);
        const current_goals_str = JSON.stringify(this.goals);
        const formatted_diary = this.format_private_diary_for_prompt();

        const ignored_messages = game_history.get_ignored_messages_by_power(this.power_name);
        let ignored_context = "";
        if (ignored_messages && Object.keys(ignored_messages).length > 0) {
            ignored_context = "\n\nPOWERS NOT RESPONDING TO YOUR MESSAGES:\n";
            for (const [power, msgs] of Object.entries(ignored_messages)) {
                ignored_context += `${power}:\n`;
                msgs.slice(-2).forEach(msg => { // Last 2 messages
                    ignored_context += `  - Phase ${msg.phase}: ${msg.content.substring(0,100)}...\n`;
                });
            }
        } else {
            ignored_context = "\n\nAll powers have been responsive to your messages.";
        }

        const problematic_patterns: string[] = ['negotiation_summary', 'updated_relationships', 'relationship_updates', 'intent'];
        for (const pattern of problematic_patterns) {
            prompt_template_content = prompt_template_content.replace(
                new RegExp(`\\n\\s*"${pattern}"`, 'g'),
                `"${pattern}"`
            );
        }

        // Escape all curly braces in JSON examples to prevent format() from interpreting them
        // First, temporarily replace the actual template variables
        const temp_vars: string[] = ['power_name', 'current_phase', 'messages_this_round', 'agent_goals',
                           'agent_relationships', 'board_state_str', 'ignored_messages_context',
                           'allowed_relationships_str', 'private_diary_summary'];

        let temp_template = prompt_template_content;
        // Create unique placeholders for each var first
        const placeholders = temp_vars.map((varName, index) => `<<TEMP_VAR_REPLACEMENT_${index}>>`);

        temp_vars.forEach((varName, index) => {
            temp_template = temp_template.replace(new RegExp(`{${varName}}`, 'g'), placeholders[index]);
        });

        // Now escape all remaining braces (which should be JSON)
        temp_template = temp_template.replace(/{/g, '{{').replace(/}/g, '}}');

        // Restore the template variables
        temp_vars.forEach((varName, index) => {
            temp_template = temp_template.replace(new RegExp(placeholders[index], 'g'), `{${varName}}`);
        });
        prompt_template_content = temp_template;

        const format_vars: Record<string, string> = {
            "power_name": this.power_name,
            "current_phase": game.current_short_phase,
            "board_state_str": board_state_str,
            "messages_this_round": messages_this_round,
            "agent_relationships": current_relationships_str,
            "agent_goals": current_goals_str,
            "allowed_relationships_str": ALLOWED_RELATIONSHIPS.join(", "),
            "private_diary_summary": formatted_diary,
            "ignored_messages_context": ignored_context
        };

        try {
            full_prompt = prompt_template_content;
            for (const [key, value] of Object.entries(format_vars)) {
                // Ensure global replacement for each key
                full_prompt = full_prompt.split(`{${key}}`).join(value);
            }
            logger.info(`[${this.power_name}] Successfully formatted prompt template after preprocessing.`);
            // success_status = "Using prompt file with preprocessing"; // Status will be updated based on outcome
        } catch (e: any) {
            logger.error(`[${this.power_name}] Error formatting negotiation diary prompt template: ${e.message}. Skipping diary entry.`);
            success_status = "Failure: Template formatting error";
            return; // Logged in finally
        }

        logger.debug(`[${this.power_name}] Negotiation diary prompt:\n${full_prompt.substring(0,500)}...`);

        raw_response = await run_llm_and_log({
            client: this.client,
            prompt: full_prompt,
            log_file_path: log_file_path,
            power_name: this.power_name,
            phase: game.current_short_phase,
            response_type: 'negotiation_diary_raw',
        });

        logger.debug(`[${this.power_name}] Raw negotiation diary response: ${raw_response.substring(0,300)}...`);

        let parsed_data: any = null;
        try {
            parsed_data = this._extract_json_from_text(raw_response);
            logger.debug(`[${this.power_name}] Parsed diary data: ${JSON.stringify(parsed_data)}`);
            success_status = "Success: Parsed diary data"; // Initial success state after parsing
        } catch (e: any) {
            logger.error(`[${this.power_name}] Failed to parse JSON from diary response: ${e.message}. Response: ${raw_response.substring(0,300)}...`);
            success_status = "Failure: JSON Parsing Error";
            // Let it proceed to add_diary_entry with fallback text
        }

        let diary_entry_text = "(LLM diary entry generation or parsing failed.)"; // Fallback
        let relationships_updated = false;

        if (parsed_data) { // Check if parsed_data is not null and is an object
            let diary_text_candidate: string | null = null;
            for (const key of ['negotiation_summary', 'summary', 'diary_entry']) {
                if (parsed_data[key] && typeof parsed_data[key] === 'string' && parsed_data[key].trim()) {
                    diary_text_candidate = parsed_data[key].trim();
                    logger.info(`[${this.power_name}] Successfully extracted '${key}' for diary.`);
                    break;
                }
            }
            if (diary_text_candidate) {
                diary_entry_text = diary_text_candidate;
            } else {
                logger.warn(`[${this.power_name}] Could not find valid summary field in diary response. Using fallback.`);
            }

            let new_relationships: Record<string, string> | null = null;
            for (const key of ['relationship_updates', 'updated_relationships', 'relationships']) {
                if (parsed_data[key] && typeof parsed_data[key] === 'object' && !Array.isArray(parsed_data[key]) && parsed_data[key] !== null) {
                    new_relationships = parsed_data[key];
                    logger.info(`[${this.power_name}] Successfully extracted '${key}' for relationship updates.`);
                    break;
                }
            }

            if (new_relationships && typeof new_relationships === 'object') {
                const valid_new_rels: Record<string, string> = {};
                for (const [p, r_val] of Object.entries(new_relationships)) { // r_val to avoid conflict with r in script
                    const p_upper = String(p).toUpperCase();
                    // Ensure r_val is a string before calling string methods
                    const r_title = typeof r_val === 'string' ? (r_val.charAt(0).toUpperCase() + r_val.slice(1).toLowerCase()) : '';

                    if (ALL_POWERS.has(p_upper) && p_upper !== this.power_name && ALLOWED_RELATIONSHIPS.includes(r_title)) {
                        valid_new_rels[p_upper] = r_title;
                    } else if (p_upper !== this.power_name) { // Log invalid relationship for a valid power
                        logger.warn(`[${this.power_name}] Invalid relationship '${r_val}' for power '${p}' in diary update. Keeping old.`);
                    }
                }

                if (Object.keys(valid_new_rels).length > 0) {
                    for (const [p_changed, new_r_val_updated] of Object.entries(valid_new_rels)) {
                        const old_r_val = this.relationships[p_changed] || "Unknown";
                        if (old_r_val !== new_r_val_updated) {
                            logger.info(`[${this.power_name}] Relationship with ${p_changed} changing from ${old_r_val} to ${new_r_val_updated} based on diary.`);
                        }
                    }
                    this.relationships = { ...this.relationships, ...valid_new_rels };
                    relationships_updated = true;
                    success_status = "Success: Applied diary data (relationships updated)"; // More specific success
                } else {
                    logger.info(`[${this.power_name}] No valid relationship updates found in diary response.`);
                    if (success_status === "Success: Parsed diary data") { // If only parsing was successful before
                         success_status = "Success: Parsed, no valid relationship updates";
                    }
                }
            } else if (new_relationships !== null) { // It was provided but not a dict (or object in JS)
                logger.warn(`[${this.power_name}] 'updated_relationships' from diary LLM was not a dictionary/object: ${typeof new_relationships}`);
            }
        }

        this.add_diary_entry(diary_entry_text, game.current_short_phase);
        if (relationships_updated) {
            this.add_journal_entry(`[${game.current_short_phase}] Relationships updated after negotiation diary: ${JSON.stringify(this.relationships)}`);
        }

        // Refine success_status if it's still the basic "Parsed diary data" but no relationships were updated.
        if (success_status === "Success: Parsed diary data" && !relationships_updated) {
            success_status = "Success: Parsed, only diary text applied";
        }

    } catch (e: any) {
        logger.error(`[${this.power_name}] Caught unexpected error in generate_negotiation_diary_entry: ${e.constructor.name}: ${e.message}`, e);
        success_status = `Failure: Exception (${e.constructor.name})`;
        // Add a fallback diary entry in case of general error, if not already handled by parsing failure
        if (!raw_response) { // Check if error happened before or during LLM call
             this.add_diary_entry(`(Error generating diary entry before LLM call: ${e.constructor.name})`, game.current_short_phase);
        } else if (success_status.startsWith("Failure: JSON Parsing Error")) {
            // Already handled by fallback text logic for diary_entry_text
        } else {
            this.add_diary_entry(`(Error generating diary entry: ${e.constructor.name})`, game.current_short_phase);
        }
    } finally {
        // Ensure log_file_path is provided and other necessary components for logging exist
        if (log_file_path) {
            log_llm_response({
                log_file_path: log_file_path,
                model_name: this.client?.model_name ?? "UnknownModel",
                power_name: this.power_name,
                phase: game?.current_short_phase ?? "UnknownPhase", // Safely access phase
                response_type: "negotiation_diary",
                raw_input_prompt: full_prompt, // This should be defined within try or be ""
                raw_response: raw_response, // This should be defined within try or be ""
                success: success_status // Reflects the final status
            });
        }
    }
  }

  public async generate_order_diary_entry(game: Game, orders: string[], log_file_path: string): Promise<void> {
    logger.info(`[${this.power_name}] Generating order diary entry for ${game.current_short_phase}...`);

    let prompt_template = _load_prompt_file('order_diary_prompt.txt');
    if (!prompt_template) {
        logger.error(`[${this.power_name}] Could not load order_diary_prompt.txt. Skipping diary entry.`);
        // No specific LLM logging here as no LLM call was made.
        this.add_diary_entry(`(Failed to load order_diary_prompt.txt for ${game.current_short_phase})`, game.current_short_phase);
        return;
    }

    const board_state_dict = game.get_state();
    const board_state_str = `Units: ${JSON.stringify(board_state_dict.units || {})}, Centers: ${JSON.stringify(board_state_dict.centers || {})}`;

    const orders_list_str = orders.length > 0 ? orders.map(o => `- ${o}`).join("\n") : "No orders submitted.";
    const goals_str = this.goals.length > 0 ? this.goals.map(g => `- ${g}`).join("\n") : "None";
    const relationships_str = Object.entries(this.relationships).length > 0
        ? Object.entries(this.relationships).map(([p, s]) => `- ${p}: ${s}`).join("\n")
        : "None";

    // Preprocessing the template to fix potential issues (similar to negotiation diary)
    const problematic_keys = ['order_summary'];
    for (const key of problematic_keys) {
        prompt_template = prompt_template.replace(new RegExp(`\\n\\s*"${key}"`, 'g'), `"${key}"`);
    }

    // Escape curly braces in JSON examples within the template
    const temp_vars = ['power_name', 'current_phase', 'orders_list_str', 'board_state_str',
                       'agent_goals', 'agent_relationships'];
    let temp_template = prompt_template;
    const placeholders = temp_vars.map((varName, index) => `<<ORDER_VAR_${index}>>`);

    temp_vars.forEach((varName, index) => {
        temp_template = temp_template.replace(new RegExp(`{${varName}}`, 'g'), placeholders[index]);
    });
    temp_template = temp_template.replace(/{/g, '{{').replace(/}/g, '}}');
    temp_vars.forEach((varName, index) => {
        temp_template = temp_template.replace(new RegExp(placeholders[index], 'g'), `{${varName}}`);
    });
    prompt_template = temp_template;

    const format_vars: Record<string, string> = {
        "power_name": this.power_name,
        "current_phase": game.current_short_phase,
        "orders_list_str": orders_list_str,
        "board_state_str": board_state_str,
        "agent_goals": goals_str,
        "agent_relationships": relationships_str
    };

    let prompt = "";
    try {
        prompt = prompt_template;
        for (const [key, value] of Object.entries(format_vars)) {
            prompt = prompt.split(`{${key}}`).join(value);
        }
        logger.info(`[${this.power_name}] Successfully formatted order diary prompt template.`);
    } catch (e: any) {
        logger.error(`[${this.power_name}] Error formatting order diary template: ${e.message}. Skipping diary entry.`);
        this.add_diary_entry(`(Error formatting order_diary_prompt.txt for ${game.current_short_phase})`, game.current_short_phase);
        // No LLM call yet, so no LLM logging.
        return;
    }

    logger.debug(`[${this.power_name}] Order diary prompt:\n${prompt.substring(0,300)}...`);

    let raw_response: string | null = null;
    let success_status = "FALSE"; // Default for LLM call
    let actual_diary_text: string | null = null;

    try {
        raw_response = await run_llm_and_log({
            client: this.client,
            prompt: prompt,
            log_file_path: log_file_path,
            power_name: this.power_name,
            phase: game.current_short_phase,
            response_type: 'order_diary', // This is for the run_llm_and_log context
        });

        if (raw_response && raw_response.trim()) {
            try {
                const response_data = this._extract_json_from_text(raw_response);
                if (response_data && typeof response_data === 'object') {
                    const diary_text_candidate = response_data.order_summary;
                    if (typeof diary_text_candidate === 'string' && diary_text_candidate.trim()) {
                        actual_diary_text = diary_text_candidate;
                        success_status = "TRUE";
                        logger.info(`[${this.power_name}] Successfully extracted 'order_summary' for order diary entry.`);
                    } else {
                        logger.warn(`[${this.power_name}] 'order_summary' missing, invalid, or empty. Value was: ${diary_text_candidate}`);
                    }
                } else {
                    logger.warn(`[${this.power_name}] Failed to parse JSON from order diary LLM response or data is not an object.`);
                }
            } catch (e: any) {
                logger.error(`[${this.power_name}] Error processing order diary JSON: ${e.message}. Raw response: ${raw_response.substring(0,200)}`);
            }
        } else {
            logger.warn(`[${this.power_name}] Empty or null response from order diary LLM.`);
        }
    } catch (e: any) {
        logger.error(`[${this.power_name}] Error during order diary LLM call: ${e.message}`, e);
        success_status = `FALSE: Exception ${e.constructor.name}`;
        // raw_response will be logged in finally
    } finally {
        // Log the LLM interaction details
        log_llm_response({
            log_file_path: log_file_path,
            model_name: this.client.model_name,
            power_name: this.power_name,
            phase: game.current_short_phase,
            response_type: 'order_diary', // This is for the CSV log type
            raw_input_prompt: prompt,
            raw_response: raw_response ?? "", // Ensure raw_response is not null
            success: success_status
        });

        if (success_status === "TRUE" && actual_diary_text) {
            this.add_diary_entry(actual_diary_text, game.current_short_phase);
            logger.info(`[${this.power_name}] Order diary entry generated and added.`);
        } else {
            const fallback_diary = `Submitted orders for ${game.current_short_phase}: ${orders.join(', ')}. (LLM failed to generate a specific diary entry or processing failed)`;
            this.add_diary_entry(fallback_diary, game.current_short_phase);
            logger.warn(`[${this.power_name}] Failed to generate specific order diary entry. Added fallback. Status: ${success_status}`);
        }
    }
  }

  public async generate_phase_result_diary_entry(
    game: Game,
    game_history: GameHistory,
    phase_summary: string,
    all_orders: Record<string, string[]>,
    log_file_path: string
  ): Promise<void> {
    logger.info(`[${this.power_name}] Generating phase result diary entry for ${game.current_short_phase}...`);

    const prompt_template = _load_prompt_file('phase_result_diary_prompt.txt');
    if (!prompt_template) {
        logger.error(`[${this.power_name}] Could not load phase_result_diary_prompt.txt. Skipping diary entry.`);
        this.add_diary_entry(`(Failed to load phase_result_diary_prompt.txt for ${game.current_short_phase} analysis)`, game.current_short_phase);
        return;
    }

    let all_orders_formatted = "";
    for (const [power, orders] of Object.entries(all_orders)) {
        const orders_str = orders.length > 0 ? orders.join(", ") : "No orders";
        all_orders_formatted += `${power}: ${orders_str}\n`;
    }

    const your_orders = all_orders[this.power_name] || [];
    const your_orders_str = your_orders.length > 0 ? your_orders.join(", ") : "No orders";

    const messages_this_phase = game_history.get_messages_by_phase(game.current_short_phase);
    let your_negotiations = "";
    messages_this_phase.forEach(msg => {
        if (msg.sender === this.power_name) {
            your_negotiations += `To ${msg.recipient}: ${msg.content}\n`;
        } else if (msg.recipient === this.power_name) {
            your_negotiations += `From ${msg.sender}: ${msg.content}\n`;
        }
    });
    if (!your_negotiations) {
        your_negotiations = "No negotiations this phase";
    }

    const relationships_str = Object.entries(this.relationships)
        .map(([p, r]) => `${p}: ${r}`)
        .join("\n");

    const goals_str = this.goals.length > 0 ? this.goals.map(g => `- ${g}`).join("\n") : "None";

    const format_vars = {
        power_name: this.power_name,
        current_phase: game.current_short_phase,
        phase_summary: phase_summary,
        all_orders_formatted: all_orders_formatted,
        your_negotiations: your_negotiations,
        pre_phase_relationships: relationships_str,
        agent_goals: goals_str,
        your_actual_orders: your_orders_str
    };

    let prompt = prompt_template;
    try {
        for (const [key, value] of Object.entries(format_vars)) {
            prompt = prompt.split(`{${key}}`).join(String(value));
        }
        logger.debug(`[${this.power_name}] Phase result diary prompt:\n${prompt.substring(0,500)}...`);
    } catch (e: any) {
        logger.error(`[${this.power_name}] Error formatting phase result diary template: ${e.message}. Skipping diary entry.`);
        this.add_diary_entry(`(Error formatting phase_result_diary_prompt.txt for ${game.current_short_phase})`, game.current_short_phase);
        return;
    }

    let raw_response = "";
    let success_status = "FALSE";

    try {
        raw_response = await run_llm_and_log({
            client: this.client,
            prompt: prompt,
            log_file_path: log_file_path,
            power_name: this.power_name,
            phase: game.current_short_phase,
            response_type: 'phase_result_diary', // For run_llm_and_log context
        });

        if (raw_response && raw_response.trim()) {
            const diary_entry = raw_response.trim();
            this.add_diary_entry(diary_entry, game.current_short_phase);
            success_status = "TRUE";
            logger.info(`[${this.power_name}] Phase result diary entry generated and added.`);
        } else {
            const fallback_diary = `Phase ${game.current_short_phase} completed. Orders executed as: ${your_orders_str}. (Failed to generate detailed analysis - empty LLM response)`;
            this.add_diary_entry(fallback_diary, game.current_short_phase);
            logger.warn(`[${this.power_name}] Empty response from LLM. Added fallback phase result diary.`);
            // success_status remains "FALSE"
        }

    } catch (e: any) {
        logger.error(`[${this.power_name}] Error generating phase result diary: ${e.message}`, e);
        const fallback_diary = `Phase ${game.current_short_phase} completed. Unable to analyze results due to error: ${e.message}`;
        this.add_diary_entry(fallback_diary, game.current_short_phase);
        success_status = `FALSE: ${e.constructor.name}`;
    } finally {
        log_llm_response({
            log_file_path: log_file_path,
            model_name: this.client.model_name,
            power_name: this.power_name,
            phase: game.current_short_phase,
            response_type: 'phase_result_diary', // For CSV log type
            raw_input_prompt: prompt,
            raw_response: raw_response,
            success: success_status
        });
    }
  }

  public log_state(prefix: string = ""): void {
    logger.debug(`[${this.power_name}] ${prefix} State: Goals=${JSON.stringify(this.goals)}, Relationships=${JSON.stringify(this.relationships)}`);
  }

  public async analyze_phase_and_update_state(
    game: Game,
    board_state: any, // Replace 'any' with a more specific type later
    phase_summary: string,
    game_history: GameHistory,
    log_file_path: string
  ): Promise<void> {
    const power_name = this.power_name;
    const current_phase_for_logging = game.get_current_phase(); // For logging context
    logger.info(`[${power_name}] Analyzing phase ${current_phase_for_logging} outcome to update state...`);
    this.log_state(`Before State Update (${current_phase_for_logging})`);

    let prompt = ""; // Define prompt variable in a higher scope for logging in finally
    let response: string | null = null; // Define response variable for logging

    try {
        const prompt_template = _load_prompt_file('state_update_prompt.txt');
        if (!prompt_template) {
            logger.error(`[${power_name}] Could not load state_update_prompt.txt. Skipping state update.`);
            return;
        }

        if (!game_history || !game_history.phases || game_history.phases.length === 0) {
            logger.warn(`[${power_name}] No game history available to analyze for ${game.current_short_phase}. Skipping state update.`);
            return;
        }

        const last_phase = game_history.phases[game_history.phases.length - 1];
        const last_phase_name = last_phase.name;

        const last_phase_summary = phase_summary; // Parameter is used directly
        if (!last_phase_summary) {
            logger.warn(`[${power_name}] No summary available for previous phase ${last_phase_name}. Skipping state update.`);
            return;
        }

        // const possible_orders = game.get_all_possible_orders(); // Not directly used in Python prompt string, but passed to build_context_prompt
        // const formatted_diary = this.format_private_diary_for_prompt(); // Same as above

        // The Python code builds 'context' via build_context_prompt but then doesn't directly use it in prompt.format for state_update_prompt.txt
        // It seems state_update_prompt.txt is self-contained or uses different variables.
        // We will replicate the direct formatting from the Python version.

        const other_powers = game.powers.filter(p => p !== power_name);

        let board_state_str = "Board State:\n";
        if (board_state && board_state.powers) {
            for (const [p_name, power_data] of Object.entries(board_state.powers as Record<string, any>)) {
                const units = power_data.units || [];
                const centers = power_data.centers || [];
                board_state_str += `  ${p_name}: Units=${JSON.stringify(units)}, Centers=${JSON.stringify(centers)}\n`;
            }
        }

        const current_year = last_phase_name && last_phase_name.length >= 5 ? last_phase_name.substring(1, 5) : "unknown";

        const format_vars = {
            power_name: power_name,
            current_year: current_year,
            current_phase: last_phase_name,
            board_state_str: board_state_str,
            phase_summary: last_phase_summary,
            other_powers: JSON.stringify(other_powers),
            current_goals: this.goals.length > 0 ? this.goals.map(g => `- ${g}`).join("\n") : "None",
            current_relationships: JSON.stringify(this.relationships) || "None"
        };

        prompt = prompt_template;
        for (const [key, value] of Object.entries(format_vars)) {
            prompt = prompt.split(`{${key}}`).join(String(value));
        }
        logger.debug(`[${power_name}] State update prompt:\n${prompt}`);

        response = await run_llm_and_log({
            client: this.client,
            prompt: prompt,
            log_file_path: log_file_path,
            power_name: power_name,
            phase: current_phase_for_logging,
            response_type: 'state_update', // For run_llm_and_log context
        });
        logger.debug(`[${power_name}] Raw LLM response for state update: ${response}`);

        let log_entry_response_type = 'state_update';
        let log_entry_success = "FALSE";
        let update_data: any = null;

        if (response && response.trim()) {
            try {
                update_data = this._extract_json_from_text(response);
                logger.debug(`[${power_name}] Successfully parsed JSON: ${JSON.stringify(update_data)}`);

                if (typeof update_data !== 'object' || update_data === null) {
                    logger.warn(`[${power_name}] Extracted data is not an object, type: ${typeof update_data}`);
                    update_data = {}; // Prevent errors below
                }

                const goals_present_and_valid = Array.isArray(update_data.updated_goals) || Array.isArray(update_data.goals);
                const rels_present_and_valid = typeof update_data.updated_relationships === 'object' && !Array.isArray(update_data.updated_relationships) ||
                                             typeof update_data.relationships === 'object' && !Array.isArray(update_data.relationships);

                if (Object.keys(update_data).length > 0 && (goals_present_and_valid || rels_present_and_valid)) {
                    log_entry_success = "TRUE";
                } else if (Object.keys(update_data).length > 0) {
                    log_entry_success = "PARTIAL";
                    log_entry_response_type = 'state_update_partial_data';
                } else {
                    log_entry_success = "FALSE";
                    log_entry_response_type = 'state_update_parsing_empty_or_invalid_data';
                }
            } catch (e: any) {
                logger.error(`[${power_name}] Failed to parse JSON response for state update: ${e.message}. Raw response: ${response}`);
                log_entry_response_type = 'state_update_json_error';
                update_data = {}; // Ensure update_data is an object for fallback logic
            }
        } else {
            logger.error(`[${power_name}] No valid response (None or empty) received from LLM for state update.`);
            log_entry_response_type = 'state_update_no_response';
            update_data = {}; // Ensure update_data is an object for fallback logic
        }

        log_llm_response({
            log_file_path: log_file_path,
            model_name: this.client.model_name,
            power_name: power_name,
            phase: current_phase_for_logging,
            response_type: log_entry_response_type,
            raw_input_prompt: prompt,
            raw_response: response ?? "",
            success: log_entry_success
        });

        if (!update_data || !(Array.isArray(update_data.updated_goals) || Array.isArray(update_data.goals) || (typeof update_data.updated_relationships === 'object' && update_data.updated_relationships !== null) || (typeof update_data.relationships === 'object' && update_data.relationships !== null) )) {
             logger.warn(`[${power_name}] update_data is None or missing essential valid structures after LLM call. Using existing goals and relationships as fallback.`);
             update_data = { // Ensure it's an object
                updated_goals: this.goals,
                updated_relationships: this.relationships,
             };
             logger.warn(`[${power_name}] Using existing goals and relationships as fallback: ${JSON.stringify(update_data)}`);
        }

        let updated_goals_list = update_data.updated_goals ?? update_data.goals;
        let updated_relationships_map = update_data.updated_relationships ?? update_data.relationships;

        if (Array.isArray(updated_goals_list)) {
            this.goals = updated_goals_list;
            this.add_journal_entry(`[${game.current_short_phase}] Goals updated based on ${last_phase_name}: ${JSON.stringify(this.goals)}`);
        } else {
            logger.warn(`[${power_name}] LLM did not provide valid 'updated_goals' list in state update.`);
        }

        if (typeof updated_relationships_map === 'object' && updated_relationships_map !== null && !Array.isArray(updated_relationships_map)) {
            const valid_new_relationships: Record<string, string> = {};
            let invalid_count = 0;

            for (const [p_key, r_value] of Object.entries(updated_relationships_map as Record<string,string>)) {
                const p_upper = p_key.toUpperCase();
                if (ALL_POWERS.has(p_upper) && p_upper !== power_name) {
                    const r_title = typeof r_value === 'string' ? (r_value.charAt(0).toUpperCase() + r_value.slice(1).toLowerCase()) : '';
                    if (ALLOWED_RELATIONSHIPS.includes(r_title)) {
                        valid_new_relationships[p_upper] = r_title;
                    } else {
                        invalid_count++;
                        if (invalid_count <= 2) {
                            logger.warn(`[${power_name}] Received invalid relationship label '${r_value}' for '${p_key}'. Ignoring.`);
                        }
                    }
                } else if (p_upper !== power_name) { // Don't log for own power
                    invalid_count++;
                    if (invalid_count <= 2) {
                        logger.warn(`[${power_name}] Received relationship for invalid/own power '${p_key}' (normalized: ${p_upper}). Ignoring.`);
                    }
                }
            }

            if (invalid_count > 2) {
                logger.warn(`[${power_name}] ${invalid_count} total invalid relationships were ignored.`);
            }

            if (Object.keys(valid_new_relationships).length > 0) {
                this.relationships = { ...this.relationships, ...valid_new_relationships }; // Merge updates
                this.add_journal_entry(`[${game.current_short_phase}] Relationships updated based on ${last_phase_name}: ${JSON.stringify(valid_new_relationships)}`);
            } else if (Object.keys(updated_relationships_map).length > 0) {
                logger.warn(`[${power_name}] Found relationships in LLM response but none were valid after normalization.`);
            } else {
                 logger.warn(`[${power_name}] LLM did not provide 'updated_relationships' dict in state update or it was empty.`);
            }
        } else {
             logger.warn(`[${power_name}] LLM did not provide valid 'updated_relationships' object in state update.`);
        }

    } catch (e: any) { // Catches errors from _load_prompt_file, formatting, or any other unexpected error
        logger.error(`[${power_name}] Error during state analysis/update for phase ${game.current_short_phase}: ${e.message}`, e);
        // Log LLM call if it happened and failed, or log failure before LLM call
        log_llm_response({
            log_file_path: log_file_path,
            model_name: this.client?.model_name ?? "UnknownModel",
            power_name: power_name,
            phase: current_phase_for_logging,
            response_type: response ? 'state_update_exception_after_llm' : 'state_update_exception_before_llm',
            raw_input_prompt: prompt, // Log prompt if available
            raw_response: response ?? `Error: ${e.message}`,
            success: "FALSE"
        });
    }

    this.log_state(`After State Update (${game.current_short_phase})`);
  }

  public update_goals(new_goals: string[]): void {
    this.goals = new_goals;
    this.add_journal_entry(`Goals updated: ${JSON.stringify(this.goals)}`);
    logger.info(`[${this.power_name}] Goals updated to: ${JSON.stringify(this.goals)}`);
  }

  public update_relationship(other_power: string, status: string): void {
    if (other_power !== this.power_name) {
        this.relationships[other_power] = status;
        this.add_journal_entry(`Relationship with ${other_power} updated to ${status}.`);
        logger.info(`[${this.power_name}] Relationship with ${other_power} set to ${status}.`);
    } else {
        logger.warn(`[${this.power_name}] Attempted to set relationship with self.`);
    }
  }

  public get_agent_state_summary(): string {
    let summary = `Agent State for ${this.power_name}:\n`;
    summary += `  Goals: ${JSON.stringify(this.goals)}\n`;
    summary += `  Relationships: ${JSON.stringify(this.relationships)}\n`;
    summary += `  Journal Entries: ${this.private_journal.length}`;
    return summary;
  }

  public async generate_plan(game: Game, board_state: any, game_history: GameHistory): Promise<string> {
    logger.info(`Agent ${this.power_name} generating strategic plan...`);
    try {
        const plan = await this.client.get_plan(game, board_state, this.power_name, game_history);
        this.add_journal_entry(`Generated plan for phase ${game.current_phase}:\n${plan}`);
        logger.info(`Agent ${this.power_name} successfully generated plan.`);
        return plan;
    } catch (e: any) {
        logger.error(`Agent ${this.power_name} failed to generate plan: ${e.message}`);
        this.add_journal_entry(`Failed to generate plan for phase ${game.current_phase} due to error: ${e.message}`);
        return "Error: Failed to generate plan.";
    }
  }
}

// Export the class and interfaces if needed by other modules
export { DiplomacyAgent, BaseModelClient, Game, GameHistory, DiplomacyAgentArgs, ALL_POWERS, ALLOWED_RELATIONSHIPS };
