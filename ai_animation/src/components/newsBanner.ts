import { gameState } from "../gameState";
import { config } from "../config";
import { GamePhase } from "../types/gameState";
import { ScheduledEvent } from "../events";


const bannerEl = document.getElementById('news-banner-content');
if (!bannerEl) throw Error("News banner not properly initialized")

export function createUpdateNewsBannerEvent(phase: GamePhase): ScheduledEvent {
  return new ScheduledEvent(`updateNewsBanner-${phase.name}`, () => { clearNewsBanner(); addToNewsBanner(phase.summary) })
}

function clearNewsBanner() {
  bannerEl.textContent = ''
}
/**
 * Appends text to the scrolling news banner.
 * If the banner is at its default text or empty, replace it entirely.
 * Otherwise, just append " | " + newText.
 * @param newText Text to add to the news banner
 */
function addToNewsBanner(newText: string): void {
  if (!bannerEl) {
    console.warn("News banner element not found");
    return;
  }

  if (config.isDebugMode) {
    console.log(`Adding to news banner: "${newText}"`);
  }

  // Add a fade-out transition
  const transitionDuration = config.uiTransitionDuration;
  bannerEl.style.transition = `opacity ${transitionDuration}s ease-out`;
  bannerEl.style.opacity = '0';

  bannerEl.textContent = newText;

  // Fade back in
  bannerEl.style.opacity = '1';
}
