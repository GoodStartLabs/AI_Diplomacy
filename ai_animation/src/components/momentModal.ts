import { gameState } from '../gameState';
import { config } from '../config';
import { getPowerDisplayName } from '../utils/powerNames';
import { PowerENUM } from '../types/map';
import { Moment } from '../types/moments';
import { MessageSchemaType } from '../types/gameState';
import { ScheduledEvent } from '../events.ts'
import { animateMessageWords, createChatBubble } from './chatBubble.ts';

interface MomentDialogueOptions {
  moment: Moment;
  power1?: PowerENUM;
  power2?: PowerENUM;
  messages?: MessageSchemaType[];
  title?: string;
  onClose?: () => void;
}

let dialogueOverlay: HTMLElement | null = null;

/**
 * Shows a dialogue box displaying conversation between two powers
 * @param options Configuration for the dialogue display
 */
export function showMomentModal(options: MomentDialogueOptions): void {
  const { moment, power1, power2, title, onClose } = options;

  // Close any existing dialogue
  closeMomentModal();

  if (moment.raw_messages.length === 0) {
    throw new Error(
      `High-interest moment detected between ${power1} and ${power2} but no messages found. ` +
      `This indicates a data quality issue - moments should only be created when there are actual conversations to display.`
    );
  }
  if (moment.powers_involved.length < 2) {
    console.warn("Attempted to show moment with only one power involved")
    onClose()
  }

  if (moment.raw_messages.length > config.convertsationModalMaxMessages) {
    moment.raw_messages = moment.raw_messages.slice(moment.raw_messages.length - config.convertsationModalMaxMessages, moment.raw_messages.length)
  }
  showConversationModalSequence(title, moment, onClose);
}

export function createMomentEvent(moment: Moment): ScheduledEvent {
  return new ScheduledEvent(
    `moment-${moment.phase}`,
    () => new Promise<void>((resolve) => {
      showMomentModal({
        moment,
        onClose: () => resolve()
      });
    }))

}

/**
 * Shows the conversation modal and sequences all messages through the event queue
 */
function showConversationModalSequence(
  title: string | undefined,
  moment: Moment,
  onClose?: () => void,
  power1?: string,
  power2?: string,
): void {
  // Create overlay
  dialogueOverlay = createDialogueOverlay();

  if (!power1 || !power2) {
    power1 = moment.powers_involved[0]
    power2 = moment.powers_involved[1]
  }

  // Create dialogue container
  const dialogueContainer = createDialogueContainer(power1, power2, title, moment);

  // Create conversation area and append to the conversation wrapper
  const conversationWrapper = dialogueContainer.querySelector('div[style*="flex: 2"]') as HTMLElement;
  const conversationArea = createConversationArea();
  conversationWrapper.appendChild(conversationArea);

  // Add close button
  const closeButton = createCloseButton();
  dialogueContainer.appendChild(closeButton);

  // Add to overlay
  dialogueOverlay.appendChild(dialogueContainer);
  document.body.appendChild(dialogueOverlay);

  dialogueOverlay!.style.opacity = '1'

  // Schedule messages to be displayed sequentially through event queue
  console.log(`Starting two-power conversation with ${moment.raw_messages.length} messages`);
  scheduleMessageSequence(conversationArea, moment.raw_messages, power1, power2).then(() => {
    closeMomentModal();
    onClose();
  });
}

/**
 * Schedules all messages to be displayed sequentially using promises
 */
async function scheduleMessageSequence(
  container: HTMLElement,
  messages: MessageSchemaType[],
  power1: string,
  power2: string,
  callbackOnClose?: () => void
): Promise<void> {
  // Chain message animations using promises to ensure sequential display
  for (let i = 0; i < messages.length; i++) {
    const messageObj = messages[i];

    // Create the message element
    const messageElement = createMessageElement(messageObj, power1, power2);
    container.appendChild(messageElement);

    // Animate message appearance
    messageElement.style.opacity = '0';
    messageElement.style.transform = 'translateY(20px)';
    messageElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    messageElement.style.opacity = '1';
    messageElement.style.transform = 'translateY(0)';

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;

    // Wait for word-by-word animation to complete
    const messageBubble = messageElement.querySelector('.message-bubble') as HTMLElement;
    if (messageBubble) {
      await new Promise<void>((resolve) => {
        animateMessageWords(messageObj.message, messageBubble, container, resolve);
      });
    }
  }

  if (callbackOnClose) {
    callbackOnClose();
  }
}

/**
 * Displays a single message with word-by-word animation
 */
function displaySingleMessage(
  container: HTMLElement,
  message: MessageSchemaType,
  power1: string,
  power2: string,
  callbackFn?: () => void
): void {
  const messageElement = createMessageElement(message, power1, power2);
  container.appendChild(messageElement);

  // Animate message appearance
  messageElement.style.opacity = '0';
  messageElement.style.transform = 'translateY(20px)';
  messageElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
  messageElement.style.opacity = '1';
  messageElement.style.transform = 'translateY(0)';

  // Scroll to bottom
  container.scrollTop = container.scrollHeight;

  // Start word-by-word animation for the message content
  const messageBubble = messageElement.querySelector('.message-bubble');
  if (messageBubble) {
    animateMessageWords(message.message, messageBubble as HTMLElement, container, callbackFn);
  } else {
    // Fallback if message bubble not found
    if (callbackFn) callbackFn();
  }
}

/**
 * Closes the two-power conversation dialogue
 * @param immediate If true, removes overlay immediately without animation
 */
export function closeMomentModal(immediate: boolean = false): void {
  dialogueOverlay = document.getElementById("dialogue-overlay")
  if (dialogueOverlay) {
    if (immediate) {
      // Immediate cleanup for phase transitions
      if (dialogueOverlay?.parentNode) {
        dialogueOverlay.parentNode.removeChild(dialogueOverlay);
      }
      dialogueOverlay = null;
    } else {
      if (dialogueOverlay?.parentNode) {
        dialogueOverlay.parentNode.removeChild(dialogueOverlay);
      }
      dialogueOverlay = null;
    }
  }
}

/**
 * Creates the main overlay element
 */
function createDialogueOverlay(): HTMLElement {
  const overlay = document.createElement('div');
  overlay.id = 'dialogue-overlay';
  return overlay;
}

/**
 * Creates the main dialogue container
 */
function createDialogueContainer(power1: string, power2: string, title?: string, moment?: Moment): HTMLElement {
  const container = document.createElement('div');
  container.className = "dialogue-container"

  // Create header section with title and moment info
  const headerSection = document.createElement('div');
  headerSection.id = "dialogue-header"

  // Add main title
  const titleElement = document.createElement('h2');
  titleElement.textContent = title || `Conversation: ${getPowerDisplayName(power1 as PowerENUM)} & ${getPowerDisplayName(power2 as PowerENUM)}`;
  titleElement.style.cssText = `
        margin: 0 0 10px 0;
        color: #4f3b16;
        font-family: 'Times New Roman', serif;
        font-size: 24px;
        font-weight: bold;
    `;
  headerSection.appendChild(titleElement);

  // Add moment type if available
  if (moment) {
    const momentTypeElement = document.createElement('div');
    momentTypeElement.textContent = `${moment.category} (Interest: ${moment.interest_score}/10)`;
    momentTypeElement.style.cssText = `
        background: rgba(75, 59, 22);
        color: #f7ecd1;
        padding: 5px 15px;
        border-radius: 15px;
        display: inline-block;
        font-size: 14px;
        font-weight: bold;
        margin-bottom: 5px;
    `;
    headerSection.appendChild(momentTypeElement);

    // Add moment description if available
    if (moment.promise_agreement || moment.actual_action || moment.impact) {
      const momentDescription = document.createElement('div');
      let description = '';
      if (moment.promise_agreement) description += `Promise: ${moment.promise_agreement}. `;
      if (moment.actual_action) description += `Action: ${moment.actual_action}. `;
      if (moment.impact) description += `Impact: ${moment.impact}`;

      momentDescription.textContent = description;
      momentDescription.style.cssText = `
        font-size: 0.9rem;
        color: #5a4b2b;
        font-style: italic;
        margin: 5px 20px 0 20px;
        line-height: 1.4;
      `;
      headerSection.appendChild(momentDescription);
    }
  }

  container.appendChild(headerSection);

  // Create main content area with three columns: diary1, conversation, diary2
  const mainContent = document.createElement('div');
  mainContent.style.cssText = `
        flex: 1;
        display: flex;
        gap: 15px;
        height: 100%;
overflow-y: auto;
    `;

  // Left diary box for power1
  const diary1Box = createDiaryBox(power1 as PowerENUM, moment?.diary_context?.[power1 as PowerENUM] || '');
  mainContent.appendChild(diary1Box);

  // Center conversation area
  const conversationWrapper = document.createElement('div');
  conversationWrapper.style.cssText = `
        flex: 2;
        display: flex;
        flex-direction: column;
        min-height: 0;
        max-height: 100%;
        overflow: hidden;
    `;
  mainContent.appendChild(conversationWrapper);

  // Right diary box for power2
  const diary2Box = createDiaryBox(power2 as PowerENUM, moment?.diary_context?.[power2 as PowerENUM] || '');
  mainContent.appendChild(diary2Box);

  container.appendChild(mainContent);

  return container;
}

/**
 * Creates a diary box for displaying power-specific thoughts and context
 */
function createDiaryBox(power: PowerENUM, diaryContent: string): HTMLElement {
  const diaryBox = document.createElement('div');
  diaryBox.className = `diary-box diary-${power.toLowerCase()}`;
  diaryBox.style.cssText = `
        flex: 1;
        min-height: 0;
        background: rgba(255, 255, 255);
        border: 2px solid #8b7355;
        border-radius: 8px;
        padding: 10px;
        display: flex;
        flex-direction: column;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    `;

  // Power name header
  const powerHeader = document.createElement('h4');
  powerHeader.textContent = `${getPowerDisplayName(power)} Diary`;
  powerHeader.className = `power-${power.toLowerCase()}`;
  powerHeader.style.cssText = `
        margin: 0 0 10px 0;
        font-size: 0.875rem;
        font-weight: bold;
        text-align: center;
        padding: 5px;
        background: rgba(75, 59, 22, 0.8);
        border-radius: 4px;
        border-bottom: 1px solid #8b7355;
    `;
  diaryBox.appendChild(powerHeader);

  // Diary content area
  const contentArea = document.createElement('div');
  contentArea.className = 'diary-content';
  contentArea.style.cssText = `
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        font-size: 1.4rem;
        line-height: 1.4;
        color: #4a3b1f;
        font-style: italic;
    `;

  if (diaryContent.trim()) {
    // Split diary content into paragraphs for better readability
    const paragraphs = diaryContent.split('\n').filter(p => p.trim());
    paragraphs.forEach((paragraph, index) => {
      const p = document.createElement('p');
      p.textContent = paragraph.trim();
      p.style.cssText = `
            margin: 0 0 4px 0;
            padding: 3px;
            background: ${index % 2 === 0 ? 'rgba(255,255,255)' : 'transparent'};
            border-radius: 3px;
        `;
      contentArea.appendChild(p);
    });
  } else {
    // No diary content available
    const noDiaryMsg = document.createElement('div');
    noDiaryMsg.textContent = 'No diary entries available for this moment.';
    noDiaryMsg.style.cssText = `
        color: #8b7355;
        font-style: italic;
        text-align: center;
        padding: 20px;
    `;
    contentArea.appendChild(noDiaryMsg);
  }

  diaryBox.appendChild(contentArea);
  return diaryBox;
}

/**
 * Creates the conversation display area
 */
function createConversationArea(): HTMLElement {
  const area = document.createElement('div');
  area.className = 'conversation-area';
  area.style.cssText = `
        flex: 1;
        min-height: 0;
        max-height: 100%;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 8px;
        border: 2px solid #8b7355;
        border-radius: 5px;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        flex-direction: column;
        gap: 8px;
        box-sizing: border-box;
    `;

  return area;
}

/**
 * Creates a close button
 */
function createCloseButton(): HTMLElement {
  const button = document.createElement('button');
  button.textContent = 'X';
  button.className = 'close-button';
  button.style.cssText = `
        position: absolute;
        top: 10px;
        right: 15px;
        background: none;
        border: none;
        font-size: 30px;
        color: #4f3b16;
        cursor: pointer;
        padding: 0;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
    `;

  button.addEventListener('mouseenter', () => {
    button.style.color = '#8b0000';
    button.style.transform = 'scale(1.1)';
  });

  button.addEventListener('mouseleave', () => {
    button.style.color = '#4f3b16';
    button.style.transform = 'scale(1)';
  });

  return button;
}

/**
 * Sets up event listeners for the dialogue
 */
function setupEventListeners(onClose?: () => void): void {
  if (!dialogueOverlay) return;

  const closeButton = dialogueOverlay.querySelector('.close-button');
  const handleClose = () => {
    closeMomentModal(true); // immediate close for manual actions
    onClose?.();

    // When manually closed, still advance phase if playing
    if (gameState.isPlaying) {
      import('../phase').then(({ _setPhase }) => {
        _setPhase(gameState.phaseIndex + 1);
      });
    }
  };

  // Close button click
  closeButton?.addEventListener('click', handleClose);

  // Escape key
  const handleKeydown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleClose();
      document.removeEventListener('keydown', handleKeydown);
    }
  };
  document.addEventListener('keydown', handleKeydown);

  // Click outside to close
  dialogueOverlay.addEventListener('click', (e) => {
    if (e.target === dialogueOverlay) {
      handleClose();
    }
  });
}


/**
 * Creates a message element for display
 */
function createMessageElement(message: MessageSchemaType, power1: string, power2: string): HTMLElement {
  const messageDiv = document.createElement('div');
  const isFromPower1 = message.sender.toUpperCase() === power1.toUpperCase();

  messageDiv.className = `message ${isFromPower1 ? 'power1' : 'power2'}`;
  messageDiv.style.cssText = `
        display: flex;
        flex-direction: column;
        align-items: ${isFromPower1 ? 'flex-start' : 'flex-end'};
        margin: 3px 0;
    `;

  // Sender label
  const senderLabel = document.createElement('div');
  senderLabel.textContent = getPowerDisplayName(message.sender as PowerENUM);
  senderLabel.className = `power-${message.sender.toLowerCase()}`;
  senderLabel.style.cssText = `
        font-size: 11px;
        font-weight: bold;
        margin-bottom: 3px;
        color: #4f3b16;
    `;

  // Message bubble (initially empty for word-by-word animation)
  const messageBubble = document.createElement('div');
  messageBubble.className = 'message-bubble';
  messageBubble.style.cssText = `
        background: ${isFromPower1 ? '#e6f3ff' : '#fff3e6'};
        border: 2px solid ${isFromPower1 ? '#4a90e2' : '#e67e22'};
        border-radius: 12px;
        padding: 6px 10px;
        max-width: 70%;
        word-wrap: break-word;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        font-size: 1.2rem;
        line-height: 1.3;
    `;

  messageDiv.appendChild(senderLabel);
  messageDiv.appendChild(messageBubble);

  return messageDiv;
}

