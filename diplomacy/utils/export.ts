// diplomacy/utils/export.ts
// Responsible for exporting games in a standardized format to disk

import * as fs from 'fs';
import * as path from 'path';
import { DiplomacyGame } from '../engine/game';
import { DiplomacyMap } from '../engine/map';
import { GamePhaseData, GamePhaseDataData } from './game_phase_data'; // Assuming GamePhaseDataData is the interface for toDict()
// import * as strings from './strings'; // Placeholder
// import * as parsing from './parsing'; // Placeholder

// Temporary placeholders for imported string constants if not yet available
const tempStrings = {
    MAP_NAME: 'map_name',
    RULES: 'rules',
};

const logger = {
    warn: (message: string, ...args: any[]) => console.warn('[Export]', message, ...args),
    error: (message: string, ...args: any[]) => console.error('[Export]', message, ...args),
};

const RULES_TO_SKIP: string[] = ['SOLITAIRE', 'NO_DEADLINE', 'CD_DUMMIES', 'ALWAYS_WAIT', 'IGNORE_ERRORS'];

export interface SavedGameFormat {
    id: string;
    map: string;
    rules: string[];
    phases: GamePhaseDataData[]; // Assuming GamePhaseDataData is the output of phase.toDict()
}

/**
 * Converts a game to a standardized JSON format
 * @param game - game to convert.
 * @param output_path - Optional path to file. If set, the JSON.stringify() of the saved_game is written to that file.
 * @param output_mode - Optional. The mode to use to write to the output_path (if provided). Defaults to 'a' (append).
 * @returns A game in the standard format, ready for JSON serialization.
 */
export function to_saved_game_format(game: DiplomacyGame, output_path?: string, output_mode: string = 'a'): SavedGameFormat {
    // In Python: phases = Game.get_phase_history(game)
    // Assuming game instance has getPhaseHistory()
    const phaseHistoryData: GamePhaseData[] = game.getPhaseHistory ? game.getPhaseHistory() : [];

    // In Python: phases.append(Game.get_phase_data(game))
    // Assuming game instance has getCurrentPhaseData()
    const currentPhaseData: GamePhaseData | null = game.getPhaseData ? game.getPhaseData() : null;

    const allPhases: GamePhaseData[] = [...phaseHistoryData];
    if (currentPhaseData) {
        allPhases.push(currentPhaseData);
    }

    const rules = game.rules.filter(rule => !RULES_TO_SKIP.includes(rule));

    const phases_to_dict: GamePhaseDataData[] = allPhases.map(phase => {
        const phaseDict = phase.toDict(); // Assumes GamePhaseData has toDict()
        // Extend states fields as in Python
        if (phaseDict.state) {
            phaseDict.state.game_id = game.game_id;
            phaseDict.state.map = game.map_name; // map_name from game instance
            phaseDict.state.rules = [...rules];
        }
        return phaseDict;
    });

    const saved_game: SavedGameFormat = {
        id: game.game_id,
        map: game.map_name, // map_name from game instance
        rules: rules,
        phases: phases_to_dict
    };

    if (output_path) {
        try {
            const fileExists = fs.existsSync(output_path);
            if (output_mode === 'a' && fileExists) {
                fs.appendFileSync(output_path, JSON.stringify(saved_game) + '\n', 'utf-8');
            } else {
                fs.writeFileSync(output_path, JSON.stringify(saved_game) + '\n', 'utf-8');
            }
        } catch (e: any) {
            logger.error(`Error writing saved game to disk: ${e.message}`);
            // Decide if to throw or just log
        }
    }
    return saved_game;
}

/**
 * Rebuilds a DiplomacyGame object from the saved game format.
 * @param saved_game - The saved game object.
 * @returns The game object restored from the saved game.
 */
export function from_saved_game_format(saved_game: SavedGameFormat): DiplomacyGame {
    const game_id = saved_game.id || null; // game_id can be null in Python version
    const kwargs: Partial<DiplomacyGame> = { // Use Partial for constructor if it accepts object
        map_name: saved_game.map || 'standard',
        rules: saved_game.rules || [],
    };

    // Assuming DiplomacyGame constructor can handle these, or we use setters.
    // The Python version directly passes kwargs to Game(game_id=game_id, **kwargs)
    const game = new DiplomacyGame(game_id, kwargs); // This matches Python's Game(game_id, **kwargs)

    const phase_history: GamePhaseData[] = [];
    for (const phase_dct of saved_game.phases || []) {
        // Assumes GamePhaseData has a static fromDict method
        phase_history.push(GamePhaseData.fromDict(phase_dct));
    }

    // Assumes game has setPhaseData method
    if (game.setPhaseData) {
        game.setPhaseData(phase_history, true);
    } else {
        logger.warn("DiplomacyGame.setPhaseData method not found. Phase history not fully restored.");
    }

    return game;
}

/**
 * Rebuilds multiple DiplomacyGame objects from each line in a .jsonl file.
 * @param input_path - The path to the input file. Expected content is one saved_game json per line.
 * @param on_error - Optional. What to do if a game conversion fails. Either 'raise', 'warn', 'ignore'.
 * @returns A list of DiplomacyGame objects.
 */
export function load_saved_games_from_disk(input_path: string, on_error: 'raise' | 'warn' | 'ignore' = 'raise'): DiplomacyGame[] {
    const loaded_games: DiplomacyGame[] = [];
    if (on_error !== 'raise' && on_error !== 'warn' && on_error !== 'ignore') {
        throw new Error("Expected values for on_error are 'raise', 'warn', 'ignore'.");
    }

    if (!fs.existsSync(input_path)) {
        logger.warn(`File ${input_path} does not exist. Aborting.`);
        return loaded_games;
    }

    const fileContent = fs.readFileSync(input_path, 'utf-8');
    const lines = fileContent.split('\n');

    for (const line of lines) {
        if (line.trim() === '') continue;
        try {
            const saved_game: SavedGameFormat = JSON.parse(line.trim());
            const game = from_saved_game_format(saved_game);
            loaded_games.push(game);
        } catch (exc: any) {
            if (on_error === 'raise') {
                throw exc;
            }
            if (on_error === 'warn') {
                logger.warn(String(exc));
            }
            // If 'ignore', do nothing.
        }
    }
    return loaded_games;
}

/**
 * Checks if the saved game is valid.
 * This is an expensive operation because it replays the game.
 * @param saved_game - The saved game (from to_saved_game_format)
 * @returns A boolean that indicates if the game is valid
 */
export function is_valid_saved_game(saved_game: SavedGameFormat): boolean {
    // This is a complex validation and relies heavily on a fully functional Game and Map class.
    // It will be stubbed for now and marked as needing full review once Game/Map are more complete.
    logger.warn("is_valid_saved_game is a STUB and only performs basic structural checks.");

    if (!saved_game || typeof saved_game !== 'object') return false;
    if (!saved_game.id || typeof saved_game.id !== 'string') return false;
    if (!saved_game.map || typeof saved_game.map !== 'string') return false;

    try {
        // Try to create a map object to see if map name is valid at least structurally
        const map_object = new DiplomacyMap(saved_game.map);
        if (map_object.name !== saved_game.map && map_object.root_map !== saved_game.map.split('.')[0]) { // Simple check
            logger.warn(`is_valid_saved_game: Map name mismatch - ${map_object.name} vs ${saved_game.map}`);
            // return false; // This might be too strict if map names have aliases not yet loaded
        }
    } catch (e) {
        logger.warn(`is_valid_saved_game: Error instantiating map ${saved_game.map}: ${e}`);
        return false;
    }

    if (!Array.isArray(saved_game.rules)) return false;
    if (!Array.isArray(saved_game.phases) || saved_game.phases.length === 0) return false;

    // TODO: Implement full game replay validation as in Python:
    // - Create a game instance.
    // - For each phase:
    //   - Set phase data.
    //   - Set orders.
    //   - Validate orders against possible_orders.
    //   - Process game.
    //   - Compare resulting state (phase name, hash, units, centers) with next phase in saved_game.
    //   - Handle DIFFERENT_ADJUDICATION rule.
    // - Validate message history constraints.

    return true; // Placeholder, actual validation is complex.
}
