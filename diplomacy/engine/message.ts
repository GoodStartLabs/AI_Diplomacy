// diplomacy/engine/message.ts

// Logger (Optional, but good practice for consistency)
const logger = {
  debug: (message: string) => console.debug('[Message]', message),
  // Add other levels if needed
};

// --- Placeholders for diplomacy.utils.* ---
// Assuming diploStrings might be used if model field names were not directly mapped
// For now, directly using property names.
// const diploStrings = {
//   SENDER: 'sender', RECIPIENT: 'recipient', TIME_SENT: 'time_sent',
//   PHASE: 'phase', MESSAGE: 'message',
// };

// --- Constants for special sender/recipient types ---
export const SYSTEM_SENDER = 'SYSTEM';
export const GLOBAL_RECIPIENT = 'GLOBAL';
export const OBSERVER_RECIPIENT = 'OBSERVER';
export const OMNISCIENT_RECIPIENT = 'OMNISCIENT';

export interface DiplomacyMessageData {
  sender: string;
  recipient: string;
  time_sent?: number | null; // Optional in constructor, server assigns
  phase: string;
  message: string;
}

export class DiplomacyMessage implements DiplomacyMessageData {
  sender: string;
  recipient: string;
  time_sent: number | null;
  phase: string;
  message: string;

  constructor(data: DiplomacyMessageData) {
    this.sender = data.sender;
    this.recipient = data.recipient;
    this.time_sent = data.time_sent !== undefined ? data.time_sent : null;
    this.phase = data.phase;
    this.message = data.message;
  }

  toStringCustom(): string {
    return `[${this.time_sent === null ? 0 : this.time_sent}/${this.phase}/${this.sender}->${this.recipient}](${this.message})`;
  }

  // For direct comparison or sorting, one might access time_sent directly.
  // Implementing all comparison methods as in Python is possible but often not idiomatic
  // if direct property access and standard array sort are sufficient.

  equals(other: DiplomacyMessage): boolean {
    return this.time_sent === other.time_sent;
  }

  isLessThan(other: DiplomacyMessage): boolean {
    if (this.time_sent === null || other.time_sent === null) {
        // Consistent handling for nulls, e.g., nulls are considered less than numbers
        return this.time_sent === null && other.time_sent !== null;
    }
    return this.time_sent < other.time_sent;
  }

  // Add other comparison methods (isGreaterThan, isLessThanOrEqual, etc.) if needed.

  is_global(): boolean {
    return this.recipient === GLOBAL_RECIPIENT;
  }

  for_observer(): boolean {
    return this.recipient === OBSERVER_RECIPIENT;
  }

  // If explicit JSON serialization/deserialization similar to Jsonable is needed:
  toJSON(): DiplomacyMessageData {
    return {
      sender: this.sender,
      recipient: this.recipient,
      time_sent: this.time_sent,
      phase: this.phase,
      message: this.message,
    };
  }

  static fromJSON(data: DiplomacyMessageData): DiplomacyMessage {
    return new DiplomacyMessage(data);
  }
}

// Example usage:
// const msg = new DiplomacyMessage({
//   sender: "FRANCE",
//   recipient: "ENGLAND",
//   phase: "S1901M",
//   message: "Hello there!",
//   time_sent: Date.now() * 1000 // Example timestamp
// });
// console.log(msg.toStringCustom());
