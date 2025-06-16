import { gameState } from "./gameState";
import { logger } from "./logger";

/**
 * Helper function to get a DOM element by ID and throw an error if not found
 * @param id The element ID to search for
 * @returns The HTMLElement
 * @throws Error if element is not found
 */
function getRequiredElement(id: string): HTMLElement {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Element with ID '${id}' not found`);
  }
  return element;
}

/**
 * Helper function to get a typed DOM element by ID and throw an error if not found
 * @param id The element ID to search for
 * @returns The typed HTMLElement
 * @throws Error if element is not found
 */
function getRequiredTypedElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id) as T;
  if (!element) {
    throw new Error(`Element with ID '${id}' not found`);
  }
  return element;
}

export function updatePhaseDisplay() {
  const currentPhase = gameState.gameData.phases[gameState.phaseIndex];

  // Add fade-out effect
  phaseDisplay.style.transition = 'opacity 0.3s ease-out';
  phaseDisplay.style.opacity = '0';

  // Update text after fade-out
  gameState.eventQueue.scheduleDelay(300, () => {
    phaseDisplay.textContent = `Era: ${currentPhase.name || 'Unknown Era'}`;
    // Fade back in
    phaseDisplay.style.opacity = '1';
  }, `phase-display-update-${Date.now()}`);
}

export function updateGameIdDisplay() {
  // Add fade-out effect
  gameIdDisplay.style.transition = 'opacity 0.3s ease-out';
  gameIdDisplay.style.opacity = '0';

  // Update text after fade-out
  gameState.eventQueue.scheduleDelay(300, () => {
    gameIdDisplay.textContent = `Game: ${gameState.gameId}`;
    // Fade back in
    gameIdDisplay.style.opacity = '1';
  }, `game-id-display-update-${Date.now()}`);
}

export function loadGameBtnFunction(file: File) {
  const reader = new FileReader();
  reader.onload = e => {
    if (e.target === null || e.target.result === null) {
      throw new Error("Failed to load file")
    }
    if (e.target.result instanceof ArrayBuffer) {
      const decoder = new TextDecoder("utf-8");
      gameState.loadGameData(decoder.decode(e.target.result))
    } else {
      gameState.loadGameData(e.target.result)
    }
  };
  reader.onerror = () => {
    logger.log("Error reading file.")
  };
  reader.readAsText(file);
}

// DOM Elements
export const loadBtn = getRequiredElement('load-btn');
export const fileInput = getRequiredTypedElement<HTMLButtonElement>('file-input');
export const prevBtn = getRequiredTypedElement<HTMLButtonElement>('prev-btn');
export const nextBtn = getRequiredTypedElement<HTMLButtonElement>('next-btn');
export const playBtn = getRequiredTypedElement<HTMLButtonElement>('play-btn');
export const speedSelector = getRequiredTypedElement<HTMLSelectElement>('speed-selector');
export const phaseDisplay = getRequiredElement('phase-display');
export const gameIdDisplay = getRequiredElement('game-id-display');
export const mapView = getRequiredElement('map-view');
export const leaderboard = getRequiredElement('leaderboard');
export const rotatingDisplay = getRequiredElement('rotating-display');

// Debug menu elements
export const debugMenu = getRequiredElement('debug-menu');
export const debugToggleBtn = getRequiredTypedElement<HTMLButtonElement>('debug-toggle-btn');
export const debugPanel = getRequiredElement('debug-panel');
export const debugCloseBtn = getRequiredTypedElement<HTMLButtonElement>('debug-close-btn');
export const provinceInput = getRequiredTypedElement<HTMLInputElement>('province-input');
export const highlightProvinceBtn = getRequiredElement('highlight-province-btn');



