import * as dotenv from 'dotenv';

// Logger setup - assuming a shared or similar logger as in other files
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

export interface Message {
  sender: string;
  recipient: string;
  content: string;
}

export interface Phase {
  name: string; // e.g. "SPRING 1901"
  plans: Record<string, string>;
  messages: Message[];
  orders_by_power: Record<string, string[]>;
  results_by_power: Record<string, string[][]>;
  phase_summaries: Record<string, string>;
  experience_updates: Record<string, string>;
}

// Helper functions that were methods on the Python Phase class
function getGlobalMessages(phase: Phase): string {
  let result = "";
  for (const msg of phase.messages) {
    if (msg.recipient === "GLOBAL") {
      result += ` ${msg.sender}: ${msg.content}\n`;
    }
  }
  return result;
}

function getPrivateMessages(phase: Phase, power: string): Record<string, string> {
  const conversations: Record<string, string> = {};
  for (const msg of phase.messages) {
    if (msg.sender === power && msg.recipient !== "GLOBAL") {
      conversations[msg.recipient] = (conversations[msg.recipient] || "") + `  ${power}: ${msg.content}\n`;
    } else if (msg.recipient === power) {
      conversations[msg.sender] = (conversations[msg.sender] || "") + `  ${msg.sender}: ${msg.content}\n`;
    }
  }
  return conversations;
}

function getAllOrdersFormatted(phase: Phase): string {
  if (Object.keys(phase.orders_by_power).length === 0) {
    return "";
  }

  let result = `\nOrders for ${phase.name}:\n`;
  for (const [power, orders] of Object.entries(phase.orders_by_power)) {
    result += `${power}:\n`;
    const results = phase.results_by_power[power] || [];
    for (let i = 0; i < orders.length; i++) {
      const order = orders[i];
      let result_str = " (successful)";
      if (i < results.length && results[i] && results[i].length > 0) {
        result_str = ` (${results[i].join(', ')})`;
      }
      result += `  ${order}${result_str}\n`;
    }
    result += "\n";
  }
  return result;
}


export class GameHistory {
  phases: Phase[];

  constructor() {
    this.phases = [];
  }

  add_phase(phase_name: string): void {
    if (this.phases.length === 0 || this.phases[this.phases.length - 1].name !== phase_name) {
      this.phases.push({
        name: phase_name,
        plans: {},
        messages: [],
        orders_by_power: {},
        results_by_power: {},
        phase_summaries: {},
        experience_updates: {},
      });
      logger.debug(`Added new phase: ${phase_name}`);
    } else {
      logger.warn(`Phase ${phase_name} already exists. Not adding again.`);
    }
  }

  private _get_phase(phase_name: string): Phase | null {
    for (let i = this.phases.length - 1; i >= 0; i--) {
      if (this.phases[i].name === phase_name) {
        return this.phases[i];
      }
    }
    logger.error(`Phase ${phase_name} not found in history.`);
    return null;
  }

  add_plan(phase_name: string, power_name: string, plan: string): void {
    const phase = this._get_phase(phase_name);
    if (phase) {
      phase.plans[power_name] = plan;
      logger.debug(`Added plan for ${power_name} in ${phase_name}`);
    }
  }

  add_message(phase_name: string, sender: string, recipient: string, message_content: string): void {
    const phase = this._get_phase(phase_name);
    if (phase) {
      phase.messages.push({ sender, recipient, content: message_content });
      logger.debug(`Added message from ${sender} to ${recipient} in ${phase_name}`);
    }
  }

  add_orders(phase_name: string, power_name: string, orders: string[]): void {
    const phase = this._get_phase(phase_name);
    if (phase) {
      if (!phase.orders_by_power[power_name]) {
        phase.orders_by_power[power_name] = [];
      }
      phase.orders_by_power[power_name].push(...orders);
      logger.debug(`Added orders for ${power_name} in ${phase_name}: ${orders}`);
    }
  }

  add_results(phase_name: string, power_name: string, results: string[][]): void {
    const phase = this._get_phase(phase_name);
    if (phase) {
      if (!phase.results_by_power[power_name]) {
        phase.results_by_power[power_name] = [];
      }
      phase.results_by_power[power_name].push(...results);
      logger.debug(`Added results for ${power_name} in ${phase_name}: ${results}`);
    }
  }

  // Python GameHistory.Phase.add_orders combines orders and results.
  // The TS version separates them for clarity. If the Python version's combined logic is crucial,
  // this needs to be refactored. Assuming separate additions for now.
  // To match Python's add_orders in Phase class:
  add_orders_and_results(phase_name: string, power: string, orders: string[], results: string[][]): void {
    const phase = this._get_phase(phase_name);
    if (phase) {
        if (!phase.orders_by_power[power]) {
            phase.orders_by_power[power] = [];
        }
        if (!phase.results_by_power[power]) {
            phase.results_by_power[power] = [];
        }
        phase.orders_by_power[power].push(...orders);
        // Pad results if necessary
        const padded_results = [...results];
        if (results.length < orders.length) {
            for (let i = 0; i < orders.length - results.length; i++) {
                padded_results.push([]);
            }
        }
        phase.results_by_power[power].push(...padded_results);
        logger.debug(`Added orders and results for ${power} in ${phase_name}`);
    }
  }


  add_phase_summary(phase_name: string, power_name: string, summary: string): void {
    const phase = this._get_phase(phase_name);
    if (phase) {
      phase.phase_summaries[power_name] = summary;
      logger.debug(`Added phase summary for ${power_name} in ${phase_name}`);
    }
  }

  add_experience_update(phase_name: string, power_name: string, update: string): void {
    const phase = this._get_phase(phase_name);
    if (phase) {
      phase.experience_updates[power_name] = update;
      logger.debug(`Added experience update for ${power_name} in ${phase_name}`);
    }
  }

  get_strategic_directives(): Record<string, string> {
    if (this.phases.length === 0) {
      return {};
    }
    return this.phases[this.phases.length - 1].plans;
  }

  get_messages_this_round(power_name: string, current_phase_name: string): string {
    const current_phase = this.phases.find(p => p.name === current_phase_name);

    if (!current_phase) {
      return `\n(No messages found for current phase: ${current_phase_name})\n`;
    }

    let messages_str = "";
    const global_msgs_content = getGlobalMessages(current_phase);
    if (global_msgs_content) {
      messages_str += "**GLOBAL MESSAGES THIS ROUND:**\n";
      messages_str += global_msgs_content;
    } else {
      messages_str += "**GLOBAL MESSAGES THIS ROUND:**\n (No global messages this round)\n";
    }

    const private_msgs_dict = getPrivateMessages(current_phase, power_name);
    if (Object.keys(private_msgs_dict).length > 0) {
      messages_str += "\n**PRIVATE MESSAGES TO/FROM YOU THIS ROUND:**\n";
      for (const [other_power, conversation_content] of Object.entries(private_msgs_dict)) {
        messages_str += ` Conversation with ${other_power}:\n`;
        messages_str += conversation_content;
        messages_str += "\n";
      }
    } else {
      messages_str += "\n**PRIVATE MESSAGES TO/FROM YOU THIS ROUND:**\n (No private messages this round)\n";
    }

    if (!global_msgs_content && Object.keys(private_msgs_dict).length === 0) {
        return `\n(No messages recorded for current phase: ${current_phase_name})\n`;
    }

    return messages_str.trim();
  }

  get_recent_messages_to_power(power_name: string, limit: number = 3): Message[] {
    if (this.phases.length === 0) {
      return [];
    }
    const recent_phases = this.phases.slice(-2); // Last 2 phases or fewer if not enough

    const messages_to_power: Message[] = [];
    for (const phase of recent_phases) {
      for (const msg of phase.messages) {
        if (msg.recipient === power_name || (msg.recipient === "GLOBAL" && msg.sender !== power_name)) {
          if (msg.sender !== power_name) { // Don't need to respond to own messages
            messages_to_power.push({ ...msg, phase: phase.name } as Message & { phase: string }); // Add phase name for context
          }
        }
      }
    }
    logger.info(`Found ${messages_to_power.length} messages to ${power_name} across ${recent_phases.length} phases`);
    if (messages_to_power.length === 0) {
        logger.info(`No messages found for ${power_name} to respond to`);
    }
    return messages_to_power.slice(-limit);
  }

  // Stubs for more complex methods to be implemented next
  get_ignored_messages_by_power(sender_name: string, num_phases: number = 3): Record<string, Array<Message & { phase: string }>> {
    const ignored_by_power: Record<string, Array<Message & { phase: string }>> = {};

    const recent_phases = this.phases.length > 0 ? this.phases.slice(-num_phases) : [];
    if (recent_phases.length === 0) {
      return ignored_by_power;
    }

    for (let i = 0; i < recent_phases.length; i++) {
      const phase = recent_phases[i];
      const sender_messages_this_phase: Array<Message & { phase_name: string }> = [];

      for (const msg of phase.messages) {
        if (msg.sender === sender_name && msg.recipient !== 'GLOBAL' && msg.recipient !== 'ALL') {
          sender_messages_this_phase.push({ ...msg, phase_name: phase.name });
        }
      }

      for (const sent_msg of sender_messages_this_phase) {
        const recipient = sent_msg.recipient;
        let found_response = false;

        // Check for responses in current phase and up to next two phases (or end of recent_phases)
        for (let j = i; j < Math.min(i + 2, recent_phases.length); j++) {
          const check_phase = recent_phases[j];
          for (const potential_reply of check_phase.messages) {
            if (
              potential_reply.sender === recipient &&
              (potential_reply.recipient === sender_name ||
              ((potential_reply.recipient === 'GLOBAL' || potential_reply.recipient === 'ALL') && potential_reply.content.includes(sender_name)))
            ) {
              found_response = true;
              break;
            }
          }
          if (found_response) break;
        }

        if (!found_response) {
          if (!ignored_by_power[recipient]) {
            ignored_by_power[recipient] = [];
          }
          // Add the original message that was ignored, with its phase context
          ignored_by_power[recipient].push({
            sender: sent_msg.sender,
            recipient: sent_msg.recipient,
            content: sent_msg.content,
            phase: sent_msg.phase_name // Store the phase in which the original message was sent
          });
        }
      }
    }
    return ignored_by_power;
  }

  get_previous_phases_history(power_name: string, current_phase_name: string, include_plans: boolean = true, num_prev_phases: number = 5): string {
    if (this.phases.length === 0) {
      return "\n(No game history available)\n";
    }

    const relevant_phases = this.phases.filter(p => p.name !== current_phase_name);

    if (relevant_phases.length === 0) {
      return "\n(No previous game history before this round)\n";
    }

    const phases_to_report = relevant_phases.slice(-num_prev_phases);

    if (phases_to_report.length === 0) {
      return "\n(No previous game history available within the lookback window)\n";
    }

    let game_history_str = "";

    for (let phase_idx = 0; phase_idx < phases_to_report.length; phase_idx++) {
      const phase = phases_to_report[phase_idx];
      let phase_content_str = `\nPHASE: ${phase.name}\n`;
      let current_phase_has_content = false;

      const global_msgs = getGlobalMessages(phase);
      if (global_msgs) {
        phase_content_str += "\n  GLOBAL MESSAGES:\n";
        phase_content_str += global_msgs.trim().split('\n').map(line => `    ${line}`).join('\n') + '\n';
        current_phase_has_content = true;
      }

      const private_msgs = getPrivateMessages(phase, power_name);
      if (Object.keys(private_msgs).length > 0) {
        phase_content_str += "\n  PRIVATE MESSAGES:\n";
        for (const [other_power, messages] of Object.entries(private_msgs)) {
          phase_content_str += `    Conversation with ${other_power}:\n`;
          phase_content_str += messages.trim().split('\n').map(line => `      ${line}`).join('\n') + '\n';
        }
        current_phase_has_content = true;
      }

      if (Object.keys(phase.orders_by_power).length > 0) {
        phase_content_str += "\n  ORDERS:\n";
        for (const [p_name, orders] of Object.entries(phase.orders_by_power)) {
          const indicator = p_name === power_name ? " (your power)" : "";
          phase_content_str += `    ${p_name}${indicator}:\n`;
          const p_results = phase.results_by_power[p_name] || [];
          for (let i = 0; i < orders.length; i++) {
            const order = orders[i];
            let result_str = " (successful)";
            // Check if results exist for this order and are not all empty strings
            if (i < p_results.length && p_results[i] && p_results[i].length > 0 && p_results[i].some(r => r !== "")) {
              result_str = ` (${p_results[i].join(', ')})`;
            }
            phase_content_str += `      ${order}${result_str}\n`;
          }
          phase_content_str += "\n";
        }
        current_phase_has_content = true;
      }

      if (current_phase_has_content) {
        if (game_history_str === "") {
          game_history_str = "**PREVIOUS GAME HISTORY (Messages, Orders, & Plans from older rounds & phases)**\n";
        }
        game_history_str += phase_content_str;
        if (phase_idx < phases_to_report.length - 1) {
          game_history_str += "  " + "-".repeat(48) + "\n";
        }
      }
    }

    if (include_plans && phases_to_report.length > 0) {
      const last_reported_previous_phase = phases_to_report[phases_to_report.length - 1];
      if (Object.keys(last_reported_previous_phase.plans).length > 0) {
        if (game_history_str === "") {
          game_history_str = "**PREVIOUS GAME HISTORY (Messages, Orders, & Plans from older rounds & phases)**\n";
        }
        game_history_str += `\n  PLANS SUBMITTED FOR PHASE ${last_reported_previous_phase.name}:\n`;
        if (last_reported_previous_phase.plans[power_name]) {
          game_history_str += `    Your Plan: ${last_reported_previous_phase.plans[power_name]}\n`;
        }
        for (const [p_other, plan_other] of Object.entries(last_reported_previous_phase.plans)) {
          if (p_other !== power_name) {
            game_history_str += `    ${p_other}'s Plan: ${plan_other}\n`;
          }
        }
        game_history_str += "\n";
      }
    }

    const header = "**PREVIOUS GAME HISTORY (Messages, Orders, & Plans from older rounds & phases)**\n";
    if (game_history_str.replace(header, "").trim() === "") {
      return "\n(No relevant previous game history to display)\n";
    }

    return game_history_str.trim();
  }
}
