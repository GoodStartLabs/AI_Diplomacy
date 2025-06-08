import * as dotenv from 'dotenv';

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

// Assuming placeholder interfaces and utility functions from other .ts files
// These would be properly imported from their respective files in a complete conversion.

// Placeholders for game objects (ideally from a diplomacy-ts library or shared types)
interface DiplomacyGame {
  powers: Record<string, { is_eliminated: () => boolean }>;
  // Add other necessary game properties/methods as used by this module
}

interface BoardState {
  phase: string; // e.g. 'S1901M'
  units: Record<string, string[]>; // e.g., { "FRANCE": ["A PAR", "F BRE"] }
  centers: Record<string, string[]>; // e.g., { "FRANCE": ["PAR", "MAR"] }
  // Other board state properties
}

// From game_history.ts (assuming it's available)
import { GameHistory } from './game_history';

// From possible_order_context.ts (assuming it's available)
import { generate_rich_order_context } from './possible_order_context';

// Placeholder for load_prompt (from utils.ts or similar)
// In a real scenario, this would be imported from a utils.ts file
const load_prompt = (filename: string): string | null => {
  logger.warn(`load_prompt called for ${filename}. Placeholder implementation.`);
  // Simplified mock responses for critical prompts
  if (filename === "context_prompt.txt") {
    return "Context for {power_name} in {current_phase}:\nUnits:\n{all_unit_locations}\nCenters:\n{all_supply_centers}\nMessages:\n{messages_this_round}\nPossible Orders:\n{possible_orders}\nGoals:\n{agent_goals}\nRelationships:\n{agent_relationships}\nDiary:\n{agent_private_diary}";
  }
  if (filename === "order_instructions.txt") {
    return "Order instructions placeholder.";
  }
  if (filename === "few_shot_example.txt") {
    return "Few shot example placeholder (unused).";
  }
  return `Content of ${filename}`;
};


export function build_context_prompt(
    game: DiplomacyGame,
    board_state: BoardState,
    power_name: string,
    possible_orders: Record<string, string[]>,
    game_history: GameHistory,
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary?: string,
): string {
    const context_template = load_prompt("context_prompt.txt");
    if (!context_template) {
        logger.error("Failed to load context_prompt.txt. Cannot build context.");
        return "Error: Context prompt template not found.";
    }

    if (agent_goals) {
        logger.debug(`Using goals for ${power_name}: ${JSON.stringify(agent_goals)}`);
    }
    if (agent_relationships) {
        logger.debug(`Using relationships for ${power_name}: ${JSON.stringify(agent_relationships)}`);
    }
    if (agent_private_diary) {
        logger.debug(`Using private diary for ${power_name}: ${agent_private_diary.substring(0,200)}...`);
    }

    const year_phase = board_state.phase;

    // Cast game to 'any' for generate_rich_order_context if its type is too restrictive or not fully defined yet
    const possible_orders_context_str = generate_rich_order_context(game as any, power_name, possible_orders);

    let messages_this_round_text = game_history.get_messages_this_round(
        power_name,
        year_phase
    );
    if (!messages_this_round_text.trim() || messages_this_round_text === "\n(No messages recorded for current phase: " + year_phase + ")\n" || messages_this_round_text === `\n(No messages found for current phase: ${year_phase})\n`) {
        messages_this_round_text = "\n(No messages this round)\n";
    }

    const units_lines: string[] = [];
    for (const [p, u_list] of Object.entries(board_state.units)) {
        const is_eliminated = game.powers[p]?.is_eliminated() || false; // Handle case where power might not be in game.powers
        units_lines.push(`  ${p}: ${u_list.join(', ')}${is_eliminated ? " [ELIMINATED]" : ""}`);
    }
    const units_repr = units_lines.join("\n");

    const centers_lines: string[] = [];
    for (const [p, c_list] of Object.entries(board_state.centers)) {
         const is_eliminated = game.powers[p]?.is_eliminated() || false;
        centers_lines.push(`  ${p}: ${c_list.join(', ')}${is_eliminated ? " [ELIMINATED]" : ""}`);
    }
    const centers_repr = centers_lines.join("\n");

    const goals_str = agent_goals && agent_goals.length > 0
        ? agent_goals.map(g => `- ${g}`).join("\n")
        : "None specified";
    const relationships_str = agent_relationships && Object.keys(agent_relationships).length > 0
        ? Object.entries(agent_relationships).map(([p, s]) => `- ${p}: ${s}`).join("\n")
        : "None specified";
    const diary_str = agent_private_diary && agent_private_diary.trim() !== ""
        ? agent_private_diary
        : "(No diary entries yet)";

    let context = context_template;
    context = context.replace("{power_name}", power_name);
    context = context.replace("{current_phase}", year_phase);
    context = context.replace("{all_unit_locations}", units_repr);
    context = context.replace("{all_supply_centers}", centers_repr);
    context = context.replace("{messages_this_round}", messages_this_round_text);
    context = context.replace("{possible_orders}", possible_orders_context_str);
    context = context.replace("{agent_goals}", goals_str);
    context = context.replace("{agent_relationships}", relationships_str);
    context = context.replace("{agent_private_diary}", diary_str);

    return context;
}

export function construct_order_generation_prompt(
    system_prompt: string | null, // Allow null for system_prompt
    game: DiplomacyGame,
    board_state: BoardState,
    power_name: string,
    possible_orders: Record<string, string[]>,
    game_history: GameHistory,
    agent_goals?: string[],
    agent_relationships?: Record<string, string>,
    agent_private_diary_str?: string,
): string {
    load_prompt("few_shot_example.txt"); // Loaded but not used, as per original logic
    const instructions = load_prompt("order_instructions.txt");
    if (!instructions) {
        logger.error("Failed to load order_instructions.txt. Cannot build order generation prompt.");
        return "Error: Order instructions not found.";
    }

    const context = build_context_prompt(
        game,
        board_state,
        power_name,
        possible_orders,
        game_history,
        agent_goals,
        agent_relationships,
        agent_private_diary: agent_private_diary_str,
    );

    if (context.startsWith("Error:")) {
        return context; // Propagate error from context building
    }

    const final_prompt = `${system_prompt || ""}\n\n${context}\n\n${instructions}`;
    return final_prompt;
}
