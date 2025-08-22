/**
 * Show Random Moment Debug Tool
 * Triggers showTwoPowerConversation for a random moment involving at least 2 powers with conversation
 */

import { gameState } from '../gameState';
import { showMomentModal } from '../components/momentModal';
import { Moment } from '../types/moments';
import { _setPhase } from '../phase';
import { config } from '../config';

/**
 * Initializes the show random moment debug tool
 * @param debugMenu - Debug menu instance to add the tool to
 */
export function initShowRandomMomentTool(debugMenu: any) {
  debugMenu.addDebugTool(
    'Show Random Moment',
    `
    <div class="debug-tool">
      <div>Status: <span id="debug-moment-status">--</span></div>
      <div>Available Moments: <span id="debug-moment-count">--</span></div>
      <button id="debug-show-random-moment">Show Random Moment</button>
      <button id="debug-refresh-moment-list">Refresh</button>
    </div>
    `,
    'Future Tools'
  );

  // Initialize the display
  updateMomentStatus();

  // Add button functionality
  const showBtn = document.getElementById('debug-show-random-moment');
  const refreshBtn = document.getElementById('debug-refresh-moment-list');

  if (showBtn) {
    showBtn.addEventListener('click', showRandomMoment);
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', updateMomentStatus);
  }
}

/**
 * Updates the moment status display in the debug menu
 */
export function updateMomentStatus() {
  const statusElement = document.getElementById('debug-moment-status');
  const countElement = document.getElementById('debug-moment-count');

  if (!statusElement || !countElement) return;

  if (!gameState.gameData || !gameState.momentsData) {
    statusElement.textContent = 'No game/moments loaded';
    countElement.textContent = '0';
    return;
  }

  const eligibleMoments = getEligibleMoments();
  statusElement.textContent = 'Ready';
  countElement.textContent = eligibleMoments.length.toString();
}

/**
 * Gets all moments that involve at least 2 powers and have conversations between them
 * @returns Array of moments eligible for conversation display
 */
function getEligibleMoments(): Moment[] {
  if (!gameState.momentsData?.moments || !gameState.gameData?.phases) {
    return [];
  }

  return gameState.momentsData.moments.filter(moment => {
    // Must involve at least 2 powers
    if (!moment.powers_involved || moment.powers_involved.length < 2) {
      return false;
    }

    // Find the phase that matches this moment
    const phase = gameState.gameData.phases.find(p => p.name === moment.phase);
    if (!phase?.messages) {
      return false;
    }

    // Check if there are messages between any pair of the involved powers
    for (let i = 0; i < moment.powers_involved.length; i++) {
      for (let j = i + 1; j < moment.powers_involved.length; j++) {
        const power1 = moment.powers_involved[i].toUpperCase();
        const power2 = moment.powers_involved[j].toUpperCase();

        const hasConversation = phase.messages.some(msg => {
          const sender = msg.sender?.toUpperCase();
          const recipient = msg.recipient?.toUpperCase();

          return (sender === power1 && recipient === power2) ||
            (sender === power2 && recipient === power1);
        });

        if (hasConversation) {
          return true;
        }
      }
    }

    return false;
  });
}

/**
 * Finds the best power pair for a given moment based on message count
 * @param moment - The moment to analyze
 * @returns Object with power1, power2, and message count, or null if no conversations found
 */
function findBestPowerPairForMoment(moment: Moment): { power1: string; power2: string; messageCount: number } | null {
  const phase = gameState.gameData.phases.find(p => p.name === moment.phase);
  if (!phase?.messages) {
    return null;
  }

  let bestPair: { power1: string; power2: string; messageCount: number } | null = null;

  // Check all pairs of involved powers
  for (let i = 0; i < moment.powers_involved.length; i++) {
    for (let j = i + 1; j < moment.powers_involved.length; j++) {
      const power1 = moment.powers_involved[i].toUpperCase();
      const power2 = moment.powers_involved[j].toUpperCase();

      const messageCount = phase.messages.filter(msg => {
        const sender = msg.sender?.toUpperCase();
        const recipient = msg.recipient?.toUpperCase();

        return (sender === power1 && recipient === power2) ||
          (sender === power2 && recipient === power1);
      }).length;

      if (messageCount > 0 && (!bestPair || messageCount > bestPair.messageCount)) {
        bestPair = { power1, power2, messageCount };
      }
    }
  }

  return bestPair;
}

/**
 * Shows a random moment from eligible moments
 */
function showRandomMoment() {
  const eligibleMoments = getEligibleMoments();

  if (eligibleMoments.length === 0) {
    console.warn('No eligible moments found for conversation display');
    const statusElement = document.getElementById('debug-moment-status');
    if (statusElement) {
      statusElement.textContent = 'No eligible moments';
      statusElement.style.color = '#ff6b6b';
      setTimeout(() => {
        statusElement.style.color = '';
        updateMomentStatus();
      }, 2000);
    }
    return;
  }

  // Pick a random moment
  const randomMoment = eligibleMoments[Math.floor(Math.random() * eligibleMoments.length)];

  // Find the best power pair for this moment
  const powerPair = findBestPowerPairForMoment(randomMoment);

  if (!powerPair) {
    console.warn('No valid power pair found for selected moment');
    return;
  }

  console.log(`Showing random moment: ${randomMoment.category} in ${randomMoment.phase}`);
  console.log(`Powers: ${powerPair.power1} & ${powerPair.power2} (${powerPair.messageCount} messages)`);
  console.log(`Interest Score: ${randomMoment.interest_score}/10`);

  // Find the phase index for this moment
  const phaseIndex = gameState.gameData.phases.findIndex(p => p.name === randomMoment.phase);

  if (phaseIndex === -1) {
    const errorMsg = `CRITICAL ERROR: Phase ${randomMoment.phase} from moment data not found in game data! This indicates a serious data integrity issue.`;
    console.error(errorMsg);

    if (config.isDebugMode) {
      alert(errorMsg + '\n\nAvailable phases: ' + gameState.gameData.phases.map(p => p.name).join(', '));
    }

    throw new Error(errorMsg);
  }

  // Set the board to the correct phase
  console.log(`Setting board to phase ${phaseIndex} (${randomMoment.phase})`);
  _setPhase(phaseIndex);

  // Show the moment using the two-power conversation display
  showMomentModal({
    power1: powerPair.power1,
    power2: powerPair.power2,
    moment: randomMoment,
    title: `Random Moment: ${randomMoment.category}`,
    onClose: () => {
      console.log('Random moment display closed');
      updateMomentStatus();
    }
  });

  // Update status to show what was triggered
  const statusElement = document.getElementById('debug-moment-status');
  if (statusElement) {
    statusElement.textContent = `Showing: ${randomMoment.category}`;
    statusElement.style.color = '#4dabf7';
  }
}
