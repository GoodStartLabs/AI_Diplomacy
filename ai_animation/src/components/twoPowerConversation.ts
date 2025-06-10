import { gameState } from '../gameState';
import { config } from '../config';
import { getPowerDisplayName } from '../utils/powerNames';
import { PowerENUM } from '../types/map';
import { Moment } from '../types/moments';

interface ConversationMessage {
  sender: string;
  recipient: string;
  message: string;
  time_sent?: string;
  [key: string]: any;
}

interface TwoPowerDialogueOptions {
  power1: string;
  power2: string;
  messages?: ConversationMessage[];
  title?: string;
  moment?: Moment;
  onClose?: () => void;
}

let dialogueOverlay: HTMLElement | null = null;

/**
 * Shows a dialogue box displaying conversation between two powers
 * @param options Configuration for the dialogue display
 */
export function showTwoPowerConversation(options: TwoPowerDialogueOptions): void {
  const { power1, power2, messages, title, moment, onClose } = options;

  // Close any existing dialogue
  closeTwoPowerConversation();

  // Get messages to display - either provided or filtered from current phase
  const conversationMessages = messages || getMessagesBetweenPowers(power1, power2);

  if (conversationMessages.length === 0) {
    console.warn(`No messages found between ${power1} and ${power2}`);
    return;
  }

  // Mark as displaying moment immediately
  gameState.isDisplayingMoment = true;

  // Schedule the conversation to be shown through event queue
  gameState.eventQueue.scheduleDelay(0, () => {
    showConversationModalSequence(power1, power2, title, moment, conversationMessages, onClose);
  }, `show-conversation-${Date.now()}`);
}

/**
 * Shows the conversation modal and sequences all messages through the event queue
 */
function showConversationModalSequence(
  power1: string, 
  power2: string, 
  title: string | undefined, 
  moment: Moment | undefined, 
  conversationMessages: ConversationMessage[], 
  onClose?: () => void
): void {
  // Create overlay
  dialogueOverlay = createDialogueOverlay();

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

  // Set up event listeners
  setupEventListeners(onClose);

  // Trigger fade in
  gameState.eventQueue.scheduleDelay(10, () => dialogueOverlay!.style.opacity = '1', `fade-in-overlay-${Date.now()}`);

  // Schedule messages to be displayed sequentially through event queue
  scheduleMessageSequence(conversationArea, conversationMessages, power1, power2);
}

/**
 * Schedules all messages to be displayed sequentially through the event queue
 */
function scheduleMessageSequence(
  container: HTMLElement,
  messages: ConversationMessage[],
  power1: string,
  power2: string
): void {
  let currentDelay = 500; // Start after modal is fully visible
  
  // Calculate timing based on mode
  const messageDisplayTime = config.isInstantMode ? 100 : config.effectivePlaybackSpeed;
  const messageAnimationTime = config.isInstantMode ? 50 : 300;
  
  messages.forEach((message, index) => {
    // Schedule each message display
    gameState.eventQueue.scheduleDelay(currentDelay, () => {
      displaySingleMessage(container, message, power1, power2);
    }, `display-message-${index}-${Date.now()}`);
    
    // Increment delay for next message
    currentDelay += messageDisplayTime + messageAnimationTime;
  });
  
  // Schedule conversation close after all messages are shown
  const totalConversationTime = currentDelay + (config.isInstantMode ? 500 : 2000); // Extra delay before closing
  gameState.eventQueue.scheduleDelay(totalConversationTime, () => {
    closeTwoPowerConversation();
    
    // After closing conversation, advance to next phase if playing
    if (gameState.isPlaying) {
      // Import _setPhase dynamically to avoid circular dependency
      import('../phase').then(({ _setPhase }) => {
        _setPhase(gameState.phaseIndex + 1);
      });
    }
  }, `close-conversation-after-messages-${Date.now()}`);
}

/**
 * Displays a single message with animation
 */
function displaySingleMessage(
  container: HTMLElement,
  message: ConversationMessage,
  power1: string,
  power2: string
): void {
  const messageElement = createMessageElement(message, power1, power2);
  container.appendChild(messageElement);

  // Animate message appearance
  messageElement.style.opacity = '0';
  messageElement.style.transform = 'translateY(20px)';

  // Use event queue for smooth animation
  gameState.eventQueue.scheduleDelay(50, () => {
    messageElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    messageElement.style.opacity = '1';
    messageElement.style.transform = 'translateY(0)';

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
  }, `animate-message-${Date.now()}`);
}

/**
 * Closes the two-power conversation dialogue
 * @param immediate If true, removes overlay immediately without animation
 */
export function closeTwoPowerConversation(immediate: boolean = false): void {
  if (dialogueOverlay) {
    if (immediate) {
      // Immediate cleanup for phase transitions
      if (dialogueOverlay?.parentNode) {
        dialogueOverlay.parentNode.removeChild(dialogueOverlay);
      }
      dialogueOverlay = null;
      gameState.isDisplayingMoment = false;
    } else {
      // Normal fade-out animation
      dialogueOverlay.classList.add('fade-out');
      gameState.eventQueue.scheduleDelay(300, () => {
        if (dialogueOverlay?.parentNode) {
          dialogueOverlay.parentNode.removeChild(dialogueOverlay);
        }
        dialogueOverlay = null;
        gameState.isDisplayingMoment = false;
      }, `close-conversation-${Date.now()}`);
    }
  }
}

/**
 * Gets messages between two specific powers from current phase
 */
function getMessagesBetweenPowers(power1: string, power2: string): ConversationMessage[] {
  const currentPhase = gameState.gameData?.phases[gameState.phaseIndex];
  if (!currentPhase?.messages) return [];

  return currentPhase.messages.filter((msg) => {
    const sender = msg.sender?.toUpperCase();
    const recipient = msg.recipient?.toUpperCase();
    const p1 = power1.toUpperCase();
    const p2 = power2.toUpperCase();

    return (sender === p1 && recipient === p2) ||
      (sender === p2 && recipient === p1);
  }).sort((a, b) => {
    // Sort by time_sent if available, otherwise maintain original order
    if (a.time_sent && b.time_sent) {
      return a.time_sent > b.time_sent;
    }
    return 0;
  });
}

/**
 * Creates the main overlay element
 */
function createDialogueOverlay(): HTMLElement {
  const overlay = document.createElement('div');
  overlay.className = 'dialogue-overlay';
  overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

  // Trigger fade in
  gameState.eventQueue.scheduleDelay(10, () => overlay.style.opacity = '1', `fade-in-overlay-${Date.now()}`);

  return overlay;
}

/**
 * Creates the main dialogue container
 */
function createDialogueContainer(power1: string, power2: string, title?: string, moment?: Moment): HTMLElement {
  const container = document.createElement('div');
  container.className = 'dialogue-container';
  container.style.cssText = `
        background: radial-gradient(ellipse at center, #f7ecd1 0%, #dbc08c 100%);
        border: 3px solid #4f3b16;
        border-radius: 8px;
        box-shadow: 0 0 15px rgba(0,0,0,0.5);
        width: 90%;
        height: 85%;
        position: relative;
        padding: 20px;
        display: flex;
        flex-direction: column;
    `;

  // Create header section with title and moment info
  const headerSection = document.createElement('div');
  headerSection.style.cssText = `
        margin-bottom: 15px;
        text-align: center;
    `;

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
        background: rgba(75, 59, 22, 0.8);
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
        background: rgba(255, 255, 255, 0.4);
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
        background: rgba(75, 59, 22, 0.1);
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
            background: ${index % 2 === 0 ? 'rgba(255,255,255,0.2)' : 'transparent'};
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
        background: rgba(255, 255, 255, 0.3);
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
    closeTwoPowerConversation(true); // immediate close for manual actions
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
function createMessageElement(message: ConversationMessage, power1: string, power2: string): HTMLElement {
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

  // Message bubble
  const messageBubble = document.createElement('div');
  messageBubble.textContent = message.message;
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
