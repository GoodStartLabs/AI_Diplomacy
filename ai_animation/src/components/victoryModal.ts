import { gameState } from '../gameState';
import { getPowerDisplayName } from '../utils/powerNames';
import { PowerENUM } from '../types/map';

interface VictoryModalOptions {
  winner: string;
  maxCenters: number;
  finalStandings: Array<{ power: string; centers: number }>;
  onClose?: () => void;
}

let victoryModalOverlay: HTMLElement | null = null;

/**
 * Shows a victory modal with the game results
 * @param options Configuration for the victory modal
 */
export function showVictoryModal(options: VictoryModalOptions): void {
  const { winner, maxCenters, finalStandings, onClose } = options;

  // Close any existing modal
  closeVictoryModal();

  // Create overlay
  victoryModalOverlay = createVictoryOverlay();

  // Create modal container
  const modalContainer = createVictoryContainer(winner, maxCenters, finalStandings);

  // Add close button if not in playing mode
  if (!gameState.isPlaying) {
    const closeButton = createCloseButton();
    modalContainer.appendChild(closeButton);
  }

  // Add to overlay
  victoryModalOverlay.appendChild(modalContainer);
  document.body.appendChild(victoryModalOverlay);

  // Set up event listeners
  setupEventListeners(onClose);

}

/**
 * Closes the victory modal
 */
export function closeVictoryModal(): void {
  if (victoryModalOverlay) {
    victoryModalOverlay.classList.add('fade-out');
    if (victoryModalOverlay?.parentNode) {
      victoryModalOverlay.parentNode.removeChild(victoryModalOverlay);
    }
    victoryModalOverlay = null;
  }
}

/**
 * Creates the main overlay element
 */
function createVictoryOverlay(): HTMLElement {
  const overlay = document.createElement('div');
  overlay.className = 'victory-modal-overlay';
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.85);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 2000;
    opacity: 0;
    transition: opacity 0.5s ease;
  `;

  // Add fade-out class styles
  const style = document.createElement('style');
  style.textContent = `
    .victory-modal-overlay.fade-out {
      opacity: 0 !important;
      transition: opacity 0.3s ease;
    }
  `;
  document.head.appendChild(style);

  // Trigger fade in
  gameState.eventQueue.scheduleDelay(10, () => overlay.style.opacity = '1', `victory-modal-fade-in-${Date.now()}`);

  return overlay;
}

/**
 * Creates the main victory container
 */
function createVictoryContainer(winner: string, maxCenters: number, finalStandings: Array<{ power: string; centers: number }>): HTMLElement {
  const container = document.createElement('div');
  container.className = 'victory-modal-container';
  container.style.cssText = `
    background: radial-gradient(ellipse at center, #f7ecd1 0%, #dbc08c 100%);
    border: 5px solid #4f3b16;
    border-radius: 12px;
    box-shadow: 0 0 30px rgba(0,0,0,0.7);
    width: 90%;
    max-width: 600px;
    position: relative;
    padding: 40px;
    text-align: center;
    font-family: "Book Antiqua", Palatino, serif;
    animation: victoryPulse 2s ease-in-out infinite alternate;
  `;

  // Add victory pulse animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes victoryPulse {
      0% { box-shadow: 0 0 30px rgba(255, 215, 0, 0.7); }
      100% { box-shadow: 0 0 50px rgba(255, 215, 0, 0.9); }
    }
  `;
  document.head.appendChild(style);

  // Victory crown/trophy
  const trophyElement = document.createElement('div');
  trophyElement.textContent = '🏆';
  trophyElement.style.cssText = `
    font-size: 64px;
    margin-bottom: 20px;
    animation: bounce 2s ease-in-out infinite;
  `;

  // Add bounce animation
  const bounceStyle = document.createElement('style');
  bounceStyle.textContent = `
    @keyframes bounce {
      0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-10px); }
      60% { transform: translateY(-5px); }
    }
  `;
  document.head.appendChild(bounceStyle);

  // Victory title
  const titleElement = document.createElement('h1');
  titleElement.textContent = 'VICTORY!';
  titleElement.style.cssText = `
    margin: 0 0 20px 0;
    color: #8b0000;
    font-size: 48px;
    font-weight: bold;
    text-shadow: 3px 3px 6px rgba(0,0,0,0.5);
    letter-spacing: 3px;
  `;

  // Winner announcement
  const winnerElement = document.createElement('h2');
  const displayName = getPowerDisplayName(winner as PowerENUM);
  winnerElement.innerHTML = `<span class="power-${winner.toLowerCase()}">${displayName}</span> WINS!`;
  winnerElement.style.cssText = `
    margin: 0 0 15px 0;
    color: #4f3b16;
    font-size: 36px;
    font-weight: bold;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
  `;

  // Supply center count
  const centersElement = document.createElement('div');
  centersElement.textContent = `${maxCenters} Supply Centers`;
  centersElement.style.cssText = `
    background: linear-gradient(90deg, #ffd700 0%, #ffed4a 100%);
    color: #8b0000;
    padding: 10px 20px;
    border-radius: 25px;
    display: inline-block;
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 30px;
    border: 3px solid #b8860b;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
  `;

  // Final standings
  const standingsElement = createStandingsElement(finalStandings);

  // Game over message
  const gameOverElement = document.createElement('div');
  gameOverElement.textContent = gameState.isPlaying ? 'Loading next game...' : 'Game Complete';
  gameOverElement.style.cssText = `
    margin-top: 20px;
    color: #666;
    font-size: 18px;
    font-style: italic;
  `;

  // Assemble container
  container.appendChild(trophyElement);
  container.appendChild(titleElement);
  container.appendChild(winnerElement);
  container.appendChild(centersElement);
  container.appendChild(standingsElement);
  container.appendChild(gameOverElement);

  return container;
}

/**
 * Creates the final standings display
 */
function createStandingsElement(finalStandings: Array<{ power: string; centers: number }>): HTMLElement {
  const standingsWrapper = document.createElement('div');
  standingsWrapper.style.cssText = `
    background: rgba(255, 255, 255, 0.4);
    border: 2px solid #8b7355;
    border-radius: 8px;
    padding: 15px;
    margin: 20px auto;
    max-width: 400px;
  `;

  const standingsTitle = document.createElement('h3');
  standingsTitle.textContent = 'Final Standings';
  standingsTitle.style.cssText = `
    margin: 0 0 15px 0;
    color: #4f3b16;
    font-size: 20px;
    font-weight: bold;
  `;

  const standingsList = document.createElement('div');
  standingsList.style.cssText = `
    display: flex;
    flex-direction: column;
    gap: 8px;
  `;

  finalStandings.forEach((entry, index) => {
    const standingItem = document.createElement('div');
    const medal = index === 0 ? "🥇" : index === 1 ? "🥈" : index === 2 ? "🥉" : `${index + 1}.`;
    const displayName = getPowerDisplayName(entry.power as PowerENUM);

    standingItem.innerHTML = `
      <span style="font-size: 18px; margin-right: 8px;">${medal}</span>
      <span class="power-${entry.power.toLowerCase()}" style="font-weight: bold;">${displayName}</span>
      <span style="margin-left: auto; font-weight: bold;">${entry.centers} centers</span>
    `;
    standingItem.style.cssText = `
      display: flex;
      align-items: center;
      padding: 8px 12px;
      background: ${index === 0 ? 'rgba(255, 215, 0, 0.3)' : 'rgba(255, 255, 255, 0.2)'};
      border-radius: 6px;
      border: 1px solid #c9b887;
    `;

    standingsList.appendChild(standingItem);
  });

  standingsWrapper.appendChild(standingsTitle);
  standingsWrapper.appendChild(standingsList);

  return standingsWrapper;
}

/**
 * Creates a close button
 */
function createCloseButton(): HTMLElement {
  const button = document.createElement('button');
  button.textContent = '×';
  button.className = 'victory-close-button';
  button.style.cssText = `
    position: absolute;
    top: 15px;
    right: 20px;
    background: none;
    border: none;
    font-size: 40px;
    color: #4f3b16;
    cursor: pointer;
    padding: 0;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all 0.2s ease;
  `;

  button.addEventListener('mouseenter', () => {
    button.style.color = '#8b0000';
    button.style.transform = 'scale(1.1)';
    button.style.backgroundColor = 'rgba(255, 255, 255, 0.3)';
  });

  button.addEventListener('mouseleave', () => {
    button.style.color = '#4f3b16';
    button.style.transform = 'scale(1)';
    button.style.backgroundColor = 'transparent';
  });

  return button;
}

/**
 * Sets up event listeners for the victory modal
 */
function setupEventListeners(onClose?: () => void): void {
  if (!victoryModalOverlay) return;

  const closeButton = victoryModalOverlay.querySelector('.victory-close-button');
  const handleClose = () => {
    closeVictoryModal();
    onClose?.();
  };

  // Close button click (only if not in playing mode)
  if (!gameState.isPlaying) {
    closeButton?.addEventListener('click', handleClose);

    // Escape key
    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
        document.removeEventListener('keydown', handleKeydown);
      }
    };
    document.addEventListener('keydown', handleKeydown);

    // Click outside to close
    victoryModalOverlay.addEventListener('click', (e) => {
      if (e.target === victoryModalOverlay) {
        handleClose();
      }
    });
  }
}
