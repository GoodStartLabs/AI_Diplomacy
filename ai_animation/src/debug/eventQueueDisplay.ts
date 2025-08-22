/**
 * Event Queue Display Window
 * Shows the current events in the gameState.eventQueue.events array
 */

import { gameState } from "../gameState";
import type { DebugMenu } from "./debugMenu";

class EventQueueDisplay {
  private container: HTMLElement | null = null;
  private isVisible: boolean = true;

  constructor() {
    this.createContainer();
  }

  private createContainer(): void {
    // Find the debug menu container
    const debugMenu = document.getElementById('debug-menu');
    if (!debugMenu) {
      console.error('Debug menu not found, cannot create event queue display');
      return;
    }

    // Check if wrapper already exists
    let wrapper = document.getElementById('debug-wrapper');
    if (!wrapper) {
      // Create wrapper for both debug menu and event queue
      wrapper = document.createElement('div');
      wrapper.id = 'debug-wrapper';

      // Move debug menu into wrapper
      debugMenu.parentNode?.insertBefore(wrapper, debugMenu);
      wrapper.appendChild(debugMenu);
    }

    // Create the event queue container
    this.container = document.createElement('div');
    this.container.id = 'event-queue-container';
    this.container.innerHTML = `
      <div class="event-queue-window">
        <div class="event-queue-header">
          <span class="event-queue-title">Event Queue</span>
          <button class="event-queue-close" title="Toggle visibility">×</button>
        </div>
        <div class="event-queue-content">
          <div class="event-queue-list"></div>
        </div>
      </div>
    `;

    // Add styles
    const existingStyle = document.getElementById('event-queue-styles');
    if (!existingStyle) {
      const style = document.createElement('style');
      style.id = 'event-queue-styles';
      style.textContent = `
        /* Wrapper for debug menu and event queue */
        #debug-wrapper {
          position: fixed;
          top: 200px;
          right: 20px;
          width: 300px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          z-index: 1000;
        }

        /* Reset debug menu positioning since it's now in the wrapper */
        #debug-wrapper #debug-menu {
          position: static !important;
          top: auto !important;
          right: auto !important;
          width: 100% !important;
        }

        #event-queue-container {
          width: 100%;
        }

        .event-queue-window {
          width: 100%;
          max-height: 400px;
          background: rgba(0, 0, 0, 0.9);
          border: 2px solid #555;
          border-radius: 8px;
          color: white;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }

        .event-queue-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: rgba(255, 255, 255, 0.1);
          border-bottom: 1px solid #555;
          border-radius: 6px 6px 0 0;
        }

        .event-queue-title {
          font-weight: bold;
          color: #fff;
        }

        .event-queue-close {
          background: none;
          border: none;
          color: #ccc;
          font-size: 16px;
          cursor: pointer;
          padding: 0;
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .event-queue-close:hover {
          color: #fff;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 3px;
        }

        .event-queue-content {
          max-height: 350px;
          overflow-y: auto;
          padding: 8px;
        }

        .event-queue-list {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .event-queue-item {
          padding: 4px 8px;
          border-radius: 4px;
          background: rgba(255, 255, 255, 0.05);
          border-left: 3px solid #666;
          word-break: break-all;
        }

        .event-queue-item.resolved {
          background: rgba(0, 255, 0, 0.1);
          border-left-color: #0f0;
          color: #ccc;
        }

        .event-queue-item.error {
          background: rgba(255, 0, 0, 0.1);
          border-left-color: #f00;
        }

        .event-queue-empty {
          padding: 20px;
          text-align: center;
          color: #666;
          font-style: italic;
        }

        #event-queue-container.hidden {
          display: none;
        }
      `;

      document.head.appendChild(style);
    }

    // Add event queue to wrapper
    wrapper.appendChild(this.container);

    // Add event listener for close button
    const closeBtn = this.container.querySelector('.event-queue-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        this.toggle();
      });
    }
  }

  updateDisplay(): void {
    if (!this.container || !this.isVisible) return;

    const listContainer = this.container.querySelector('.event-queue-list');
    if (!listContainer) return;

    const events = gameState.eventQueue.allEvents;

    if (events.length === 0) {
      listContainer.innerHTML = '<div class="event-queue-empty">No events in queue</div>';
      return;
    }

    listContainer.innerHTML = events
      .map((event, index) => {
        let className = 'event-queue-item';
        if (event.resolved) className += ' resolved';
        if (event.error) className += ' error';

        return `<div class="${className}">${index + 1}. ${event.id}</div>`;
      })
      .join('');
  }

  public show(): void {
    this.isVisible = true;
    if (this.container) {
      this.container.classList.remove('hidden');
    }
  }

  public hide(): void {
    this.isVisible = false;
    if (this.container) {
      this.container.classList.add('hidden');
    }
  }

  public toggle(): void {
    if (this.isVisible) {
      this.hide();
    } else {
      this.show();
    }
  }

  public get visible(): boolean {
    return this.isVisible;
  }

  public destroy(): void {
    if (this.container) {
      this.container.remove();
      this.container = null;
    }
  }
}

// Global instance
let eventQueueDisplay: EventQueueDisplay | null = null;

/**
 * Initialize the event queue display tool in the debug menu
 */
export function initEventQueueDisplayTool(debugMenu: DebugMenu): void {
  // Create the display window
  if (!eventQueueDisplay) {
    eventQueueDisplay = new EventQueueDisplay();
  }

  // Add toggle button to debug menu
  const content = `
    <label>
      <input type="checkbox" id="event-queue-toggle" checked> Show Event Queue
    </label>
  `;

  debugMenu.addDebugTool('Event Queue Display', content);

  // Add event listener for the toggle
  const toggle = document.getElementById('event-queue-toggle') as HTMLInputElement;
  if (toggle) {
    toggle.addEventListener('change', () => {
      if (eventQueueDisplay) {
        if (toggle.checked) {
          eventQueueDisplay.show();
        } else {
          eventQueueDisplay.hide();
        }
      }
    });
  }
  eventQueueDisplay.updateDisplay()

}

export function updateEventQueueDebugDisplay() {
  eventQueueDisplay?.updateDisplay()
}
