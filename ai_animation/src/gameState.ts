import * as THREE from "three"
import { type CoordinateData, CoordinateDataSchema, PowerENUM } from "./types/map"
import type { GameSchemaType, Message } from "./types/gameState";
import { debugMenuInstance } from "./debug/debugMenu.ts"
import { config } from "./config.ts"
import { GameSchema, type MessageSchema } from "./types/gameState";
import { prevBtn, nextBtn, playBtn, speedSelector, mapView, updateGameIdDisplay, updatePhaseDisplay } from "./domElements";
import { createChatWindows } from "./domElements/chatWindows";
import { logger } from "./logger";
import { OrbitControls } from "three/examples/jsm/Addons.js";
import { displayInitialPhase, togglePlayback } from "./phase";
import { Tween, Group as TweenGroup } from "@tweenjs/tween.js";
import { MomentsDataSchema, Moment, NormalizedMomentsData } from "./types/moments";
import { updateLeaderboard } from "./components/leaderboard";
import { closeVictoryModal } from "./components/victoryModal.ts";
import { EventQueue } from "./types/events";

//FIXME: This whole file is a mess. Need to organize and format

enum AvailableMaps {
  STANDARD = "standard"
}

/**
 * Return a random power from the PowerENUM for the player to control
 * Only returns powers that have more than 2 supply centers in the last phase
 */
function getRandomPower(gameData?: GameSchemaType): PowerENUM {
  const allPowers = Object.values(PowerENUM).filter(power =>
    power !== PowerENUM.GLOBAL && power !== PowerENUM.EUROPE
  );

  // If no game data provided, return any random power
  if (!gameData || !gameData.phases || gameData.phases.length === 0) {
    const idx = Math.floor(Math.random() * allPowers.length);
    return allPowers[idx];
  }

  // Get the last phase to check supply centers
  const lastPhase = gameData.phases[gameData.phases.length - 1];

  // Filter powers that have more than 2 supply centers
  const eligiblePowers = allPowers.filter(power => {
    const centers = lastPhase.state?.centers?.[power];
    return centers && centers.length > 2;
  });

  // If no powers have more than 2 centers, fall back to any power
  if (eligiblePowers.length === 0) {
    const idx = Math.floor(Math.random() * allPowers.length);
    return allPowers[idx];
  }

  const idx = Math.floor(Math.random() * eligiblePowers.length);
  return eligiblePowers[idx];
}

function loadFileFromServer(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    fetch(filePath)
      .then(response => {
        if (!response.ok) {
          reject(`Failed to load file: ${response.status}`);
        }

        // FIXME: This occurs because the server seems to resolve any URL to the homepage. This is the case for Vite's Dev Server.
        // Check content type to avoid HTML errors
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('text/html')) {
          reject('Received HTML instead of JSON. Check the file path.');
        }
        return response.text();
      })
      .then(data => {
        // Check for HTML content as a fallback
        if (data.trim().startsWith('<!DOCTYPE') || data.trim().startsWith('<html')) {
          reject('Received HTML instead of JSON. Check the file path.');
        }
        resolve(data)
      })
  })
}


class GameState {
  boardState!: CoordinateData
  gameId: number
  gameData!: GameSchemaType
  momentsData!: NormalizedMomentsData
  _phaseIndex: number
  boardName: string
  currentPower!: PowerENUM
  isPlaying: boolean


  //Scene for three.js
  scene: THREE.Scene

  // camera and controls
  camControls!: OrbitControls
  camera!: THREE.PerspectiveCamera
  renderer!: THREE.WebGLRenderer

  unitMeshes: THREE.Group[]

  // Animations needed for this turn
  unitAnimations: Tween[]

  // Camera Animation during playing
  cameraPanAnim!: TweenGroup

  // Global timing for animations
  globalTime: number
  deltaTime: number

  // Event queue for deterministic animations
  eventQueue: EventQueue

  constructor(boardName: AvailableMaps) {
    this._phaseIndex = 0
    this.boardName = boardName
    this.gameId = 0
    this.isPlaying = false

    this.scene = new THREE.Scene()
    this.unitMeshes = []
    this.unitAnimations = []
    this.globalTime = 0
    this.deltaTime = 0
    this.eventQueue = new EventQueue()
    this.loadBoardState()
  }
  set phaseIndex(val: number) {
    this._phaseIndex = val
    updatePhaseDisplay()
  }
  get phaseIndex() {
    return this._phaseIndex
  }

  /**
   * Load game data from a JSON string and initialize the game state
   * @param gameDataString JSON string containing game data
   * @returns Promise that resolves when game is initialized or rejects if data is invalid
   */
  loadGameData = (gameData: string): Promise<void> => {

    return new Promise((resolve, reject) => {
      try {
        this.gameData = GameSchema.parse(JSON.parse(gameData));
        // Log data structure for debugging
        console.log("Loading game data with structure:",
          `${this.gameData.phases?.length || 0} phases, ` +
          `orders format: ${this.gameData.phases?.[0]?.orders ? (Array.isArray(this.gameData.phases[0].orders) ? 'array' : 'object') : 'none'}`
        );

        // Show a sample of the first phase for diagnostic purposes
        if (this.gameData.phases && this.gameData.phases.length > 0) {
          console.log("First phase sample:", {
            name: this.gameData.phases[0].name,
            ordersCount: this.gameData.phases[0].orders ?
              (Array.isArray(this.gameData.phases[0].orders) ?
                this.gameData.phases[0].orders.length :
                Object.keys(this.gameData.phases[0].orders).length) : 0,
            ordersType: this.gameData.phases[0].orders ? typeof this.gameData.phases[0].orders : 'none',
          });
        }

        // Parse the game data using Zod schema
        logger.log(`Game data loaded: ${this.gameData.phases?.length || 0} phases found.`)

        // Reset phase index to beginning
        this.phaseIndex = 0;

        if (this.gameData.phases?.length) {
          // Enable UI controls
          prevBtn.disabled = false;
          nextBtn.disabled = false;
          playBtn.disabled = false;
          speedSelector.disabled = false;

          // Set the power if the game specifies it, else random.
          this.currentPower = this.gameData.power !== undefined ? this.gameData.power : getRandomPower(this.gameData);


          const momentsFilePath = `./games/${this.gameId}/moments.json`;
          loadFileFromServer(momentsFilePath)
            .then((data) => {
              const parsedData = JSON.parse(data);

              // FIXME: Why do we have two different moments data types?!? There should only be a single one.
              //
              // Check if this is the comprehensive format and normalize it
              if ('analysis_results' in parsedData && parsedData.analysis_results) {
                // Transform comprehensive format to animation format
                const normalizedData: NormalizedMomentsData = {
                  metadata: parsedData.metadata,
                  power_models: parsedData.metadata.power_to_model || {},
                  moments: parsedData.analysis_results.moments || []
                };
                this.momentsData = normalizedData;
              } else {
                // It's already in animation format, validate and use
                const validatedData = MomentsDataSchema.parse(parsedData);
                // Type assertion since we know this is the animation format after parsing
                this.momentsData = validatedData as NormalizedMomentsData;
              }

              logger.log(`Loaded ${this.momentsData.moments.length} moments from ${momentsFilePath}`);
            })
            .catch((error) => {
              // Continue without moments data - it's optional
              this.momentsData = null;
              throw error
            })
            .finally(() => {
              // Initialize chat windows for all powers
              createChatWindows();

              // Display the initial phase
              displayInitialPhase()

              // Update game ID display
              updateGameIdDisplay();

            })
          resolve()
        } else {
          logger.log("Error: No phases found in game data");
          reject(new Error("No phases found in game data"))
        }
      } catch (error) {
        console.error("Error parsing game data:", error);
        if (error.errors) {
          // Format Zod validation errors more clearly
          const formattedErrors = error.errors.map(err =>
            `- Path ${err.path.join('.')}: ${err.message} (got ${err.received})`
          ).join('\n');
          logger.log(`Game data validation failed:\n${formattedErrors}`);
        } else {
          logger.log(`Error parsing game data: ${error.message}`);
        }
        reject(error);
      }
    })
  }

  loadBoardState = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      fetch(`./maps/${this.boardName}/coords.json`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to load coordinates: ${response.status}`);
          }
          return response.json()
        })
        .then((data) => {
          this.boardState = CoordinateDataSchema.parse(data)
          resolve()
        })
        .catch(error => {
          console.error(error);
          reject()
          throw error
        });
    })
  }

  /**
   * Check if a power is present in the current game
   * @param power The power to check
   * @returns True if the power is present in the current phase
   */
  isPowerInGame = (power: string): boolean => {
    if (!this.gameData || !this.gameData.phases || this.phaseIndex < 0 || this.phaseIndex >= this.gameData.phases.length) {
      return false;
    }

    const currentPhase = this.gameData.phases[this.phaseIndex];

    // Check if power has units or centers in the current phase
    if (currentPhase.state?.units && power in currentPhase.state.units) {
      return true;
    }

    if (currentPhase.state?.centers && power in currentPhase.state.centers) {
      return true;
    }

    // Check if power has relationships defined
    if (currentPhase.agent_relationships && power in currentPhase.agent_relationships) {
      return true;
    }

    return false;
  }

  /*
   * Loads the next game in the order, reseting the board and gameState
   */
  loadNextGame = (setPlayback: boolean = false) => {
    // Ensure any open overlays are cleaned up before loading next game
    if (this.isDisplayingMoment) {
      // Import at runtime to avoid circular dependency
      import('./components/twoPowerConversation').then(({ closeTwoPowerConversation }) => {
        closeTwoPowerConversation(true);
      });
    }

    let gameId = this.gameId + 1
    let contPlaying = false
    if (setPlayback || this.isPlaying) {
      contPlaying = true
    }
    this.loadGameFile(gameId).then(() => {
      gameState.gameId = gameId
      if (contPlaying) {
        this.eventQueue.scheduleDelay(config.victoryModalDisplayMs, () => {
          togglePlayback(true)
        }, `load-next-game-playback-${Date.now()}`)
      }
    }).catch(() => {
      console.warn("caught error trying to advance game. Setting gameId to 0 and restarting...")
      this.loadGameFile(0)
      if (contPlaying) {
        togglePlayback(true)
      }
    }).finally(closeVictoryModal)


  }

  /*
   * Given a gameId, load that game's state into the GameState Object
   */
  loadGameFile = (gameId: number | undefined = undefined): Promise<void> => {
    if (gameId === undefined) {
      gameId = gameState.gameId
    }

    if (gameId === null || gameId < 0) {
      throw Error(`Attempted to load game with invalid ID ${gameId}`)
    }

    // Path to the default game file
    const gameFilePath = `./games/${gameId}/game.json`;
    return new Promise((resolve, reject) => {
      loadFileFromServer(gameFilePath).then((data) => {

        return this.loadGameData(data);
      })
        .then(() => {
          console.log(`Game file with id ${gameId} loaded and parsed successfully`);
          // Update rotating display and relationship popup with game data
          if (this.gameData) {
            this.gameId = gameId
            updateGameIdDisplay();
            updateLeaderboard();
            if (config.isDebugMode) {
              debugMenuInstance.updateTools()
            }
            resolve()
          }
        })
        .catch(error => {
          // Use console.error instead of logger.log to avoid updating the info panel
          console.error(`Error loading game ${gameFilePath}: ${error}`);
          reject()
        });
    })
  }

  checkPhaseHasMoment = (phaseName: string): Moment | null => {
    let momentMatch = this.momentsData.moments.filter((moment) => {
      return moment.phase === phaseName && moment.raw_messages.length > 0
    })

    // If there is more than one moment per turn, only return the largest one.
    if (momentMatch.length > 1) {
      momentMatch = momentMatch.sort((a, b) => {
        return b.interest_score - a.interest_score
      })
    }

    return momentMatch.length > 0 ? momentMatch[0] : null
  }

  createThreeScene = () => {
    if (mapView === null) {
      throw Error("Cannot find mapView element, unable to continue.")
    }

    this.scene.background = new THREE.Color(0x87CEEB);

    // Camera
    this.camera = new THREE.PerspectiveCamera(
      60,
      mapView.clientWidth / mapView.clientHeight,
      1,
      3000
    );
    this.camera.position.set(0, 800, 900); // MODIFIED: Increased z-value to account for map shift

    // Renderer with streaming optimizations
    this.renderer = new THREE.WebGLRenderer({
      powerPreference: "high-performance",
    });
    this.renderer.setSize(mapView.clientWidth, mapView.clientHeight);

    mapView.appendChild(this.renderer.domElement);

    // Controls with streaming optimizations
    this.camControls = new OrbitControls(this.camera, this.renderer.domElement);
    this.camControls.screenSpacePanning = true;
    this.camControls.minDistance = 100;
    this.camControls.maxDistance = 2000;
    this.camControls.maxPolarAngle = Math.PI / 2; // Limit so you don't flip under the map
    this.camControls.target.set(0, 0, 100); // ADDED: Set control target to new map center


    // Lighting (keep it simple)
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.6));

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
    dirLight.position.set(300, 400, 300);
    this.scene.add(dirLight);
  }
  get currentPhase() {
    return this.gameData.phases[this.phaseIndex]
  }
}


export let gameState = new GameState(AvailableMaps.STANDARD);
