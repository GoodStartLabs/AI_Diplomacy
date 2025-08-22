/**
 * Event queue system for deterministic animations
 */

import { config } from "./config";
import { debugMenuInstance } from "./debug/debugMenu";

export class ScheduledEvent {
  id: string;
  callback: () => void | Promise<void>;
  resolved?: boolean;
  running!: boolean;
  error?: Error; // If the event caused an error, store it here.
  promise?: Promise<void>;

  constructor(id: string, callback: () => void | Promise<void>, resolved?: boolean) {
    this.id = id
    this.callback = callback
    this.resolved = resolved ? true : resolved
  }

  run = () => {
    this.running = true
    // Store the promise so we can track it
    this.promise = Promise.resolve(this.callback())
      .then(() => {
        this.resolved = true;
      })
      .catch((e) => {
        this.error = e;
        this.resolved = true;
      });
  }
}

export class EventQueue {
  private events: ScheduledEvent[] = [];
  private startTime: number = 0;
  private isRunning: boolean = false;
  private currentEventPromise?: Promise<void>;

  /**
   * Start the event queue with current time as reference
   */
  start(): void {
    this.isRunning = true;
    if (this.events.length > 0) {
      this.events[0].run()
    }
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
    this.currentEventPromise = undefined;
    if (resetCallback) {
      resetCallback();
    }
  }

  /**
   * Add an event to the queue
   */
  schedule(event: ScheduledEvent): void {
    if (!event || !(event instanceof ScheduledEvent)) {
      throw new Error("Attempted to schedule an invalid event")
    }
    this.events.push(event);
  }
  scheduleMany(events: ScheduledEvent[]): void {
    for (let event of events) {
      this.schedule(event)
    }
  }


  /**
   * Update the event queue, triggering events that are ready
   */
  update(): void {
    if (!this.isRunning) return;
    if (this.events.length < 1) return;

    const currentEvent = this.events[0];

    // Start the event if not started
    if (!currentEvent.running && !currentEvent.resolved) {
      currentEvent.run();
      this.currentEventPromise = currentEvent.promise;
    }

    // Check if current event is complete
    if (currentEvent.resolved) {
      if (currentEvent.error) {
        console.error(currentEvent.error)
      }
      if (config.isDebugMode) {
        debugMenuInstance.updateTools()
      }
      this.events.shift()
      if (this.events.length > 0) {
        this.events[0].run()
      }
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
}
