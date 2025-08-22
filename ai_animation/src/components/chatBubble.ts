import { MessageSchemaType } from "../types/gameState";
import { config } from "../config";


export function createChatBubble(message: MessageSchemaType): HTMLElement {

  const messageElement = document.createElement('div');
  return messageElement
}


// New function to animate message words one at a time
/**
 * Animates message text one word at a time
 * @param message The full message text to animate
 * @param contentSpanId The ID of the span element to animate within
 * @param messagesContainer The container holding the messages
 * @param onComplete Callback function to run when animation completes
 */
export function animateMessageWords(message: string, contentSpan: HTMLElement, messagesContainer: HTMLElement, onComplete: Function | null) {
  if (!(typeof message === "string")) {
    throw new Error("Message must be a string")

  }
  const words = message.split(/\s+/);
  if (!contentSpan) {
    throw new Error("Couldn't find text bubble to fill")
  }

  // Clear any existing content
  contentSpan.textContent = '';
  let wordIndex = 0;

  // Function to add the next word
  const addNextWord = () => {
    if (wordIndex >= words.length) {
      // All words added - message is complete
      console.log(`Finished animating message with ${words.length} words in chat`);
      // Call completion callback after all words are displayed
      if (onComplete) {
        setTimeout(() => {
          onComplete();
        }, config.messageCompletionDelay || 100);
      }
      return;
    }

    // Add space if not the first word
    if (wordIndex > 0) {
      contentSpan.textContent += ' ';
    }

    // Add the next word
    contentSpan.textContent += words[wordIndex];
    wordIndex++;

    // Calculate delay based on word length and playback speed
    // Longer words get slightly longer display time
    const wordLength = words[wordIndex - 1].length;
    const delay = Math.max(config.messageWordDelay || 50, Math.min(200, (config.messageWordDelay || 50) * (wordLength / 4)));

    // Scroll to ensure newest content is visible
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Schedule next word
    setTimeout(addNextWord, delay);
  };

  // Start animation
  addNextWord();
}

