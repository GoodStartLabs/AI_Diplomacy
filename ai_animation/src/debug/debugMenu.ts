/**
 * Debug Menu Management
 * Handles the collapsible debug menu and organization of debug tools
 */

import { updateNextMomentDisplay, initNextMomentTool } from "./nextMoment";
import { initDebugProvinceHighlighting } from "./provinceHighlight";
import { initInstantChatTool as initInstantModeTool } from "./instantMode";
import { initSpeechToggleTool } from "./speechToggle";
import { initShowRandomMomentTool, updateMomentStatus } from "./showRandomMoment";
import { initPhaseJumpTool, updatePhaseJumpOptions } from "./phaseJump";
import { initEventQueueDisplayTool, toggleEventQueueDisplayState, updateEventQueueDebugDisplay } from "./eventQueueDisplay";

export class DebugMenu {
  private toggleBtn: HTMLButtonElement;
  private panel: HTMLElement;
  private closeBtn: HTMLButtonElement;
  private isExpanded: boolean = false;

  constructor() {
    this.toggleBtn = document.getElementById('debug-toggle-btn') as HTMLButtonElement;
    this.panel = document.getElementById('debug-panel') as HTMLElement;
    this.closeBtn = document.getElementById('debug-close-btn') as HTMLButtonElement;

    if (!this.toggleBtn || !this.panel || !this.closeBtn) {
      throw new Error('Debug menu elements not found in DOM');
    }

    this.initEventListeners();

    // Start with the menu open
    this.toggle()
  }

  private initEventListeners(): void {
    // Toggle button click
    this.toggleBtn.addEventListener('click', () => {
      this.toggle();
    });

    // Close button click
    this.closeBtn.addEventListener('click', () => {
      this.collapse();
    });

    // Close on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isExpanded) {
        this.collapse();
      }
    });

  }

  /**
   * Shows the debug menu
   */
  public show(): void {
    const debugMenu = document.getElementById('debug-menu');
    if (debugMenu) {
      debugMenu.style.display = 'block';
      this.initTools()
    }
  }

  /**
   * Hides the debug menu completely
   */
  public hide(): void {
    const debugMenu = document.getElementById('debug-menu');
    if (debugMenu) {
      debugMenu.style.display = 'none';
    }
    this.collapse();
  }

  /**
   * Toggles the debug panel expansion
   */
  public toggle(): void {
    if (this.isExpanded) {
      this.collapse();
    } else {
      this.expand();
    }
  }

  /**
   * Expands the debug panel
   */
  public expand(): void {
    this.panel.classList.remove('debug-panel-collapsed');
    this.panel.classList.add('debug-panel-expanded');
    this.isExpanded = true;
    this.toggleBtn.textContent = '🔧 Debug ▲';
  }

  /**
   * Collapses the debug panel
   */
  public collapse(): void {
    this.panel.classList.remove('debug-panel-expanded');
    this.panel.classList.add('debug-panel-collapsed');
    this.isExpanded = false;
    this.toggleBtn.textContent = '🔧 Debug';
  }

  /**
   * Adds a new debug tool section to the menu
   * @param title - The title of the debug section
   * @param content - HTML content for the debug tool
   * @param beforeSection - Optional: insert before this section (by title)
   */
  public addDebugTool(title: string, content: string, beforeSection?: string): void {
    const debugContent = this.panel.querySelector('.debug-content');
    if (!debugContent) return;

    // Create new section
    const section = document.createElement('div');
    section.className = 'debug-section';
    section.innerHTML = `
      <h4>${title}</h4>
      ${content}
    `;

    if (beforeSection) {
      // Find the section to insert before
      const sections = debugContent.querySelectorAll('.debug-section h4');
      for (const h4 of sections) {
        if (h4.textContent === beforeSection) {
          const targetSection = h4.parentElement;
          if (targetSection) {
            debugContent.insertBefore(section, targetSection);
            return;
          }
        }
      }
    }

    // If no specific position, insert before "Future Tools" section or at the end
    const futureToolsSection = Array.from(debugContent.querySelectorAll('.debug-section h4'))
      .find(h4 => h4.textContent === 'Future Tools')?.parentElement;

    if (futureToolsSection) {
      debugContent.insertBefore(section, futureToolsSection);
    } else {
      debugContent.appendChild(section);
    }
  }

  /**
   * Removes a debug tool section
   * @param title - The title of the section to remove
   */
  public removeDebugTool(title: string): void {
    const debugContent = this.panel.querySelector('.debug-content');
    if (!debugContent) return;

    const sections = debugContent.querySelectorAll('.debug-section h4');
    for (const h4 of sections) {
      if (h4.textContent === title) {
        const section = h4.parentElement;
        if (section) {
          section.remove();
          break;
        }
      }
    }
  }

  /**
   * Gets the current expansion state
   */
  public get expanded(): boolean {
    return this.isExpanded;
  }

  private initTools(): void {
    initEventQueueDisplayTool(this);
    initSpeechToggleTool(this);
    initInstantModeTool(this);
    initPhaseJumpTool(this);
    initNextMomentTool(this);
    initShowRandomMomentTool(this);
    initDebugProvinceHighlighting()
  }

  public updateTools(): void {
    updateNextMomentDisplay();
    updateMomentStatus();
    updatePhaseJumpOptions();
    updateEventQueueDebugDisplay();
  }
}

export let debugMenuInstance = new DebugMenu();
