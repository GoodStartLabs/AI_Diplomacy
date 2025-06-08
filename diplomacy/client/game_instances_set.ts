// diplomacy/client/game_instances_set.ts

// Logger setup (optional, as not used in Python source but good practice)
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// --- Placeholder for NetworkGame ---
// This would be imported from its actual file (e.g., ./network_game)
// It needs game_id, role, and static-like methods for role type checking.
export interface NetworkGame {
  game_id: string;
  role: string; // e.g., 'FRANCE', 'OBSERVER', 'OMNISCIENT'
  // Other properties and methods of a NetworkGame instance
}

// --- Placeholder for diplomacy.utils.exceptions ---
class DiplomacyException extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DiplomacyException";
  }
}

// --- Static-like helper functions for role checking (mimicking Game.is_player_game etc.) ---
// These would ideally be static methods on a NetworkGame class or part of a Game type definition.
// For now, they are standalone functions taking a NetworkGame object.
// The actual implementation of these checks would depend on how roles are defined (e.g. specific strings).
function isPlayerGame(game: NetworkGame): boolean {
  // Example implementation: Player roles are usually uppercase power names
  return game.role === game.role.toUpperCase() && !['OBSERVER', 'OMNISCIENT'].includes(game.role);
}

function isObserverGame(game: NetworkGame): boolean {
  return game.role === 'OBSERVER'; // Assuming 'OBSERVER' is the role string
}

function isOmniscientGame(game: NetworkGame): boolean {
  return game.role === 'OMNISCIENT'; // Assuming 'OMNISCIENT' is the role string
}


export class GameInstancesSet {
  game_id: string;
  private games: Map<string, WeakRef<NetworkGame>>; // role -> WeakRef<NetworkGame>
  current_observer_type: string | null;

  constructor(game_id: string) {
    this.game_id = game_id;
    this.games = new Map<string, WeakRef<NetworkGame>>();
    this.current_observer_type = null;
  }

  get_games(): NetworkGame[] {
    const live_games: NetworkGame[] = [];
    for (const ref of this.games.values()) {
      const game = ref.deref();
      if (game) {
        live_games.push(game);
      }
    }
    return live_games;
  }

  get(role: string): NetworkGame | undefined {
    const ref = this.games.get(role);
    return ref?.deref();
  }

  get_special(): NetworkGame | undefined {
    if (this.current_observer_type) {
      return this.get(this.current_observer_type);
    }
    return undefined;
  }

  remove(role: string): NetworkGame | undefined {
    const game_ref = this.games.get(role);
    const game_instance = game_ref?.deref();
    if (this.games.delete(role)) {
        if (role === this.current_observer_type) {
            this.current_observer_type = null;
        }
        return game_instance;
    }
    return undefined;
  }

  remove_special(): NetworkGame | undefined {
    if (this.current_observer_type) {
      return this.remove(this.current_observer_type);
    }
    return undefined;
  }

  add(game: NetworkGame): void {
    if (this.game_id !== game.game_id) {
        throw new DiplomacyException(`Game ID mismatch: Expected ${this.game_id}, got ${game.game_id}`);
    }

    if (isPlayerGame(game)) {
      if (this.games.has(game.role) && this.games.get(game.role)?.deref()) { // Check if ref exists and points to a live object
        throw new DiplomacyException(`Power name ${game.role} already in game instances set.`);
      }
    } else if (isObserverGame(game) || isOmniscientGame(game)) {
      if (this.current_observer_type !== null && this.current_observer_type !== game.role) {
        // Allow re-adding the same observer type if the previous one was GC'd or removed
        const existingSpecial = this.get(this.current_observer_type);
        if (existingSpecial) {
             throw new DiplomacyException(
                `Previous special game ${this.current_observer_type} must be removed before adding new one ${game.role}.`
             );
        }
      }
      // If adding a different type of special game or if the current one is gone
      if (this.current_observer_type && this.current_observer_type !== game.role && this.get(this.current_observer_type)) {
           throw new DiplomacyException(
                `Cannot add special game ${game.role} as ${this.current_observer_type} already exists and is different.`
            );
      }
      this.current_observer_type = game.role;
    } else {
      // Should not happen if isPlayerGame, isObserverGame, isOmniscientGame cover all cases
      throw new DiplomacyException(`Unknown game role type for game: ${game.role}`);
    }

    this.games.set(game.role, new WeakRef(game));
    logger.debug(`Added game instance for role ${game.role} in game ${this.game_id}`);
  }
}
