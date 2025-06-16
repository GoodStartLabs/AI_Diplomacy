/**
 * Event queue system for deterministic animations
 */

export interface ScheduledEvent {
  id: string;
  triggerAtTime: number;  // Relative to startTime in seconds
  callback: () => void;
  resolved?: boolean;
  priority?: number;  // Higher numbers execute first for events at same time
  error?: Error; // If the event caused an error, store it here.
}

export class EventQueue {
  private events: ScheduledEvent[] = [];
  private startTime: number = 0;
  private isRunning: boolean = false;

  /**
   * Start the event queue with current time as reference
   */
  start(): void {
    this.startTime = performance.now();
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
    let clearedQueue = this.events.filter(event => !event.resolved);
    if (clearedQueue.length <= 1) {
      console.log(this.events)
      throw new Error("We've cleared all the messages out of the queue")
    }
    this.events = clearedQueue
  }

  /**
   * Update the event queue, triggering events that are ready
   */
  update(): void {
    if (!this.isRunning) return;

    const now = performance.now();
    const elapsed = now - this.startTime;

    for (const event of this.events) {
      if (!event.resolved && elapsed >= event.triggerAtTime) {
        try {

          event.callback();
        } catch (err) {
          // TODO: Need some system here to catch and report errors, but we mark them as resolved now so that we don't call an erroring fucntion repeatedly.
          this.events.slice(this.events.indexOf(event), 1)
          if (err instanceof Error) {
            event.error = err
            console.error(err)
          } else {
            console.error(`Got type "${typeof err} as error for event with id ${event.id}`)
            console.error(err)
          }
        } finally {
          event.resolved = true;
        }
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
    const now = performance.now();
    const elapsed = this.isRunning ? now - this.startTime : 0;
    this.schedule({
      id: id || `delay-${Date.now()}-${Math.random()}`,
      triggerAtTime: elapsed + (delayMs), // Schedule relative to current time
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
    const now = performance.now();
    const startElapsed = this.isRunning ? now - this.startTime : 0;

    const scheduleNext = () => {
      counter++;
      this.schedule({
        id: `${baseId}-${counter}`,
        triggerAtTime: startElapsed + (intervalMs * counter),
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
