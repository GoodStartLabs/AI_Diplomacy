/**
 * Event queue system for deterministic animations
 */

export interface ScheduledEvent {
  id: string;
  triggerAtTime: number;  // Relative to startTime in seconds
  callback: () => void;
  resolved?: boolean;
  priority?: number;  // Higher numbers execute first for events at same time
}

export class EventQueue {
  private events: ScheduledEvent[] = [];
  private startTime: number = 0;
  private isRunning: boolean = false;

  /**
   * Start the event queue with current time as reference
   */
  start(): void {
    this.startTime = performance.now() / 1000;
    this.isRunning = true;
  }

  /**
   * Stop the event queue
   */
  stop(): void {
    this.isRunning = false;
  }

  /**
   * Reset the event queue, clearing all events
   * @param resetCallback Optional callback to run after reset (for cleanup)
   */
  reset(resetCallback?: () => void): void {
    this.events = [];
    this.isRunning = false;
    if (resetCallback) {
      resetCallback();
    }
  }

  /**
   * Add an event to the queue
   */
  schedule(event: ScheduledEvent): void {
    this.events.push(event);
    // Keep events sorted by trigger time, then by priority
    this.events.sort((a, b) => {
      if (a.triggerAtTime === b.triggerAtTime) {
        return (b.priority || 0) - (a.priority || 0);
      }
      return a.triggerAtTime - b.triggerAtTime;
    });
  }

  /**
   * Remove resolved events from the queue
   */
  cleanup(): void {
    this.events = this.events.filter(event => !event.resolved);
  }

  /**
   * Update the event queue, triggering events that are ready
   */
  update(): void {
    if (!this.isRunning) return;

    const now = performance.now() / 1000;
    const elapsed = now - this.startTime;

    for (const event of this.events) {
      if (!event.resolved && elapsed >= event.triggerAtTime) {
        event.callback();
        event.resolved = true;
      }
    }

    // Clean up resolved events periodically
    if (this.events.length > 0 && this.events.every(e => e.resolved)) {
      this.cleanup();
    }
  }

  /**
   * Get remaining events count
   */
  get pendingCount(): number {
    return this.events.filter(e => !e.resolved).length;
  }

  /**
   * Get all events (for debugging)
   */
  get allEvents(): ScheduledEvent[] {
    return [...this.events];
  }

  /**
   * Schedule a simple delay callback (like setTimeout)
   */
  scheduleDelay(delayMs: number, callback: () => void, id?: string): void {
    const now = performance.now() / 1000;
    const elapsed = this.isRunning ? now - this.startTime : 0;
    this.schedule({
      id: id || `delay-${Date.now()}-${Math.random()}`,
      triggerAtTime: elapsed + (delayMs / 1000), // Schedule relative to current time
      callback
    });
  }

  /**
   * Schedule a recurring event (like setInterval) 
   * Returns a function to cancel the recurring event
   */
  scheduleRecurring(intervalMs: number, callback: () => void, id?: string): () => void {
    let counter = 0;
    const baseId = id || `recurring-${Date.now()}`;
    const now = performance.now() / 1000;
    const startElapsed = this.isRunning ? now - this.startTime : 0;
    
    const scheduleNext = () => {
      counter++;
      this.schedule({
        id: `${baseId}-${counter}`,
        triggerAtTime: startElapsed + (intervalMs * counter) / 1000,
        callback: () => {
          callback();
          scheduleNext(); // Schedule the next occurrence
        }
      });
    };
    
    scheduleNext();
    
    // Return cancel function
    return () => {
      // Mark all future events for this recurring schedule as resolved
      this.events.forEach(event => {
        if (event.id.startsWith(baseId) && !event.resolved) {
          event.resolved = true;
        }
      });
    };
  }
}