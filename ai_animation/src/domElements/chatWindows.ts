import * as THREE from "three";
import { gameState } from "../gameState";
import { config } from "../config";
import { GamePhase, MessageSchemaType } from "../types/gameState";
import { getPowerDisplayName } from '../utils/powerNames';
import { PowerENUM } from '../types/map';
import { ScheduledEvent } from "../events";
import { createChatBubble, animateMessageWords } from "../components/chatBubble";


//TODO: Sometimes the LLMs use lists, and they don't work in the chats. The just appear as bullets within a single line.
let faceIconCache = {}; // Cache for generated face icons

// Add a message counter to track sound effect frequency
type chatWindowMap = { [key in PowerENUM]: {
  element: HTMLHtmlElement,
  messagesContainer: HTMLHtmlElement,
  isGlobal: boolean,
  seenMessages: Set<MessageSchemaType>
} }


let chatWindows: chatWindowMap

// --- CHAT WINDOW FUNCTIONS ---
export function createChatWindows() {
  // Clear existing chat windows
  const chatContainer = document.getElementById('chat-container');
  if (!chatContainer) {
    throw new Error("Could not get element with ID 'chat-container'")
  }
  chatContainer.innerHTML = '';
  chatWindows = {};

  // Create a chat window for each power (except the current power)
  const powers = [PowerENUM.AUSTRIA, PowerENUM.ENGLAND, PowerENUM.FRANCE, PowerENUM.GERMANY, PowerENUM.ITALY, PowerENUM.RUSSIA, PowerENUM.TURKEY];

  // Filter out the current power for chat windows
  const otherPowers = powers.filter(power => power !== gameState.currentPower);

  // Add a GLOBAL chat window first
  createChatWindow(PowerENUM.GLOBAL, true);

  // Create chat windows for each power except the current one
  otherPowers.forEach(power => {
    createChatWindow(power);
  });
}
// Modified to use 3D face icons properly
function createChatWindow(power, isGlobal = false) {
  const chatContainer = document.getElementById('chat-container');
  const chatWindow = document.createElement('div');
  chatWindow.className = 'chat-window';
  chatWindow.id = `chat-${power}`;
  chatWindow.style.position = 'relative'; // Add relative positioning for absolute child positioning

  // Create a slimmer header with appropriate styling
  const header = document.createElement('div');
  header.className = 'chat-header';

  // Adjust header to accommodate larger face icons
  header.style.display = 'flex';
  header.style.alignItems = 'center';
  header.style.padding = '4px 8px'; // Reduced vertical padding
  header.style.height = '24px'; // Explicit smaller height
  header.style.backgroundColor = 'rgba(78, 62, 41, 0.7)'; // Semi-transparent background
  header.style.borderBottom = '1px solid rgba(78, 62, 41, 1)'; // Solid bottom border

  // Create the title element
  const titleElement = document.createElement('span');
  if (isGlobal) {
    titleElement.style.color = '#ffffff';
    titleElement.textContent = getPowerDisplayName(PowerENUM.GLOBAL);
  } else {
    titleElement.className = `power-${power.toLowerCase()}`;
    titleElement.textContent = getPowerDisplayName(power as PowerENUM);
  }
  titleElement.style.fontWeight = 'bold'; // Make text more prominent
  titleElement.style.textShadow = '1px 1px 2px rgba(0,0,0,0.7)'; // Add text shadow for better readability
  header.appendChild(titleElement);

  // Create container for 3D face icon that floats over the header
  const faceHolder = document.createElement('div');
  faceHolder.style.width = '64px';
  faceHolder.style.height = '64px';
  faceHolder.style.position = 'absolute'; // Position absolutely
  faceHolder.style.right = '10px'; // From right edge
  faceHolder.style.top = '0px'; // ADJUSTED: Moved lower to align with the header
  faceHolder.style.cursor = 'pointer';
  faceHolder.style.borderRadius = '50%';
  faceHolder.style.overflow = 'hidden';
  faceHolder.style.boxShadow = '0 2px 5px rgba(0,0,0,0.5)';
  faceHolder.style.border = '2px solid #fff';
  faceHolder.style.zIndex = '10'; // Ensure it's above other elements
  faceHolder.id = `face-${power}`;

  // Generate the face icon and add it to the chat window (not header)
  generateFaceIcon(power).then(dataURL => {
    const img = document.createElement('img');
    img.src = dataURL;
    img.style.width = '100%';
    img.style.height = '100%';
    img.id = `face-img-${power}`; // Add ID for animation targeting

    // Add subtle idle animation
    setInterval(() => {
      if (!img.dataset.animating && Math.random() < 0.1) {
        idleAnimation(img);
      }
    }, 3000);

    faceHolder.appendChild(img);
  });

  // Create messages container with extra top padding to avoid overlap with floating head

  header.appendChild(faceHolder);

  // Create messages container
  const messagesContainer = document.createElement('div');
  messagesContainer.className = 'chat-messages';
  messagesContainer.id = `messages-${power}`;
  messagesContainer.style.paddingTop = '8px'; // Add padding to prevent content being hidden under face

  // Add toggle functionality
  header.addEventListener('click', () => {
    chatWindow.classList.toggle('chat-collapsed');
  });

  // Assemble chat window - add faceHolder directly to chatWindow, not header
  chatWindow.appendChild(header);
  chatWindow.appendChild(faceHolder);
  chatWindow.appendChild(messagesContainer);

  // Add to container
  chatContainer.appendChild(chatWindow);

  // Store reference
  chatWindows[power] = {
    element: chatWindow,
    messagesContainer: messagesContainer,
    isGlobal: isGlobal,
    seenMessages: new Set()
  };
}

function fiterAndSortChatMessagesForPhase(phase: GamePhase): MessageSchemaType[] {

  let relevantMessages = phase.messages.filter(msg => {
    return (
      msg.sender === gameState.currentPower ||
      msg.recipient === gameState.currentPower ||
      msg.recipient === 'GLOBAL'
    );
  });
  relevantMessages.sort((a, b) => a.time_sent - b.time_sent);
  return relevantMessages
}

export function createMessageEvents(phase: GamePhase): ScheduledEvent[] {
  let messageEvents: ScheduledEvent[] = []

  // Only show messages relevant to the current player (sent by them, to them, or global)
  const relevantMessages = fiterAndSortChatMessagesForPhase(phase)
  for (let [idx, msg] of relevantMessages.entries()) {
    messageEvents.push(new ScheduledEvent(
      `message-${phase.name}-${msg.sender}`,
      () => new Promise<void>((resolve) => {
        addMessageToChat(msg, !config.isInstantMode, () => resolve());
        animateHeadNod(msg, (idx % config.soundEffectFrequency === 0));
      })
    ))

  }
  return messageEvents
}


// Modified to support word-by-word animation and callback
function addMessageToChat(msg: MessageSchemaType, animateWords: boolean = false, onComplete: Function | null = null) {
  // Determine which chat window to use
  let targetPower;
  if (msg.recipient === 'GLOBAL') {
    targetPower = 'GLOBAL';
  } else {
    targetPower = msg.sender === gameState.currentPower ? msg.recipient : msg.sender;
  }
  if (!chatWindows[targetPower]) return false;

  // Create a unique ID for this message to avoid duplication
  const msgId = `${msg.sender}-${msg.recipient}-${msg.time_sent}-${msg.message}`;


  const messagesContainer = chatWindows[targetPower].messagesContainer;
  const chatBubble = createChatBubble(msg)

  // Style based on sender/recipient
  if (targetPower === 'GLOBAL') {
    // Global chat shows sender info
    const senderColor = msg.sender.toLowerCase();
    chatBubble.className = 'chat-message message-incoming';

    // Add the header with the sender name immediately
    const headerSpan = document.createElement('span');
    headerSpan.style.fontWeight = 'bold';
    headerSpan.className = `power-${senderColor}`;
    headerSpan.textContent = `${getPowerDisplayName(msg.sender as PowerENUM)}: `;
    chatBubble.appendChild(headerSpan);


  } else {
    // Private chat - outgoing or incoming style
    const isOutgoing = msg.sender === gameState.currentPower;
    chatBubble.className = `chat-message ${isOutgoing ? 'message-outgoing' : 'message-incoming'}`;

  }
  const contentSpan = document.createElement('span');
  contentSpan.id = `msg-content-${msgId.replace(/[^a-zA-Z0-9]/g, '-')}`;

  chatBubble.appendChild(contentSpan);

  // Add timestamp
  const timeDiv = document.createElement('div');
  timeDiv.className = 'message-time';
  timeDiv.textContent = gameState.currentPhase.name;
  chatBubble.appendChild(timeDiv);
  // Add to container
  messagesContainer.appendChild(chatBubble);

  // Scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  if (animateWords) {
    // Start word-by-word animation
    animateMessageWords(msg.message, contentSpan, messagesContainer, onComplete);
  } else {
    // Show entire message at once
    const contentSpan = chatBubble.querySelector(`#msg-content-${msgId.replace(/[^a-zA-Z0-9]/g, '-')}`);
    if (contentSpan) {
      contentSpan.textContent = msg.message;
    }

    // If there's a completion callback, call it immediately for non-animated messages
    if (onComplete) {
      onComplete();
    }
  }

  return true; // This was a new message
}


// Modified to support conditional sound effects
function animateHeadNod(msg, playSoundEffect = true) {
  // Determine which chat window's head to animate
  let targetPower;
  if (msg.recipient === 'GLOBAL') {
    targetPower = 'GLOBAL';
  } else {
    targetPower = msg.sender === gameState.currentPower ? msg.recipient : msg.sender;
  }

  const chatWindow = chatWindows[targetPower]?.element;
  if (!chatWindow) return;

  // Find the face image and animate it
  const img = chatWindow.querySelector(`#face-img-${targetPower}`);
  if (!img) return;

  img.dataset.animating = 'true';

  // Choose a random animation type for variety
  const animationType = Math.floor(Math.random() * 4);

  let animation;

  switch (animationType) {
    case 0: // Nod animation
      animation = img.animate([
        { transform: 'rotate(0deg) scale(1)' },
        { transform: 'rotate(15deg) scale(1.1)' },
        { transform: 'rotate(-10deg) scale(1.05)' },
        { transform: 'rotate(5deg) scale(1.02)' },
        { transform: 'rotate(0deg) scale(1)' }
      ], {
        duration: 600,
        easing: 'ease-in-out'
      });
      break;

    case 1: // Bounce animation
      animation = img.animate([
        { transform: 'translateY(0) scale(1)' },
        { transform: 'translateY(-8px) scale(1.15)' },
        { transform: 'translateY(3px) scale(0.95)' },
        { transform: 'translateY(-2px) scale(1.05)' },
        { transform: 'translateY(0) scale(1)' }
      ], {
        duration: 700,
        easing: 'ease-in-out'
      });
      break;

    case 2: // Shake animation
      animation = img.animate([
        { transform: 'translate(0, 0) rotate(0deg)' },
        { transform: 'translate(-5px, -3px) rotate(-5deg)' },
        { transform: 'translate(5px, 2px) rotate(5deg)' },
        { transform: 'translate(-5px, 1px) rotate(-3deg)' },
        { transform: 'translate(0, 0) rotate(0deg)' }
      ], {
        duration: 500,
        easing: 'ease-in-out'
      });
      break;

    case 3: // Pulse animation
      animation = img.animate([
        { transform: 'scale(1)', boxShadow: '0 0 0 0 rgba(255,255,255,0.7)' },
        { transform: 'scale(1.2)', boxShadow: '0 0 0 10px rgba(255,255,255,0)' },
        { transform: 'scale(1)', boxShadow: '0 0 0 0 rgba(255,255,255,0)' }
      ], {
        duration: 800,
        easing: 'ease-out'
      });
      break;
  }

  animation.onfinish = () => {
    img.dataset.animating = 'false';
  };

  // Trigger random snippet only if playSoundEffect is true
  if (playSoundEffect) {
    playRandomSoundEffect();
  }
}

// Generate a 3D face icon for chat windows with higher contrast
async function generateFaceIcon(power) {
  if (faceIconCache[power]) {
    return faceIconCache[power];
  }

  // Even larger renderer size for better quality
  const offWidth = 192, offHeight = 192; // Increased from 128x128 to 192x192
  const offRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  offRenderer.setSize(offWidth, offHeight);
  offRenderer.setPixelRatio(1);

  // Scene
  const offScene = new THREE.Scene();
  offScene.background = null;

  // Camera
  const offCamera = new THREE.PerspectiveCamera(45, offWidth / offHeight, 0.1, 1000);
  offCamera.position.set(0, 0, 50);

  // Power-specific colors with higher contrast/saturation
  const colorMap: Record<PowerENUM, number> = {
    [PowerENUM.GLOBAL]: 0xf5f5f5, // Brighter white
    [PowerENUM.AUSTRIA]: 0xff0000, // Brighter red
    [PowerENUM.ENGLAND]: 0x0000ff, // Brighter blue
    [PowerENUM.FRANCE]: 0x00bfff, // Brighter cyan
    [PowerENUM.GERMANY]: 0x1a1a1a, // Darker gray for better contrast
    [PowerENUM.ITALY]: 0x00cc00, // Brighter green
    [PowerENUM.RUSSIA]: 0xe0e0e0, // Brighter gray
    [PowerENUM.TURKEY]: 0xffcc00, // Brighter yellow
    [PowerENUM.EUROPE]: 0xf5f5f5, // Same as global
  };
  const headColor = colorMap[power as PowerENUM] || 0x808080;

  // Larger head geometry
  const headGeom = new THREE.BoxGeometry(20, 20, 20); // Increased from 16x16x16
  const headMat = new THREE.MeshStandardMaterial({ color: headColor });
  const headMesh = new THREE.Mesh(headGeom, headMat);
  offScene.add(headMesh);

  // Create outline for better visibility (a slightly larger black box behind)
  const outlineGeom = new THREE.BoxGeometry(22, 22, 19);
  const outlineMat = new THREE.MeshBasicMaterial({ color: 0x000000 });
  const outlineMesh = new THREE.Mesh(outlineGeom, outlineMat);
  outlineMesh.position.z = -2; // Place it behind the head
  offScene.add(outlineMesh);

  // Larger eyes with better contrast
  const eyeGeom = new THREE.BoxGeometry(3.5, 3.5, 3.5); // Increased from 2.5x2.5x2.5
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0x000000 });
  const leftEye = new THREE.Mesh(eyeGeom, eyeMat);
  leftEye.position.set(-4.5, 2, 10); // Adjusted position
  offScene.add(leftEye);
  const rightEye = new THREE.Mesh(eyeGeom, eyeMat);
  rightEye.position.set(4.5, 2, 10); // Adjusted position
  offScene.add(rightEye);

  // Add a simple mouth
  const mouthGeom = new THREE.BoxGeometry(8, 1.5, 1);
  const mouthMat = new THREE.MeshBasicMaterial({ color: 0x000000 });
  const mouth = new THREE.Mesh(mouthGeom, mouthMat);
  mouth.position.set(0, -3, 10);
  offScene.add(mouth);

  // Brighter lighting for better contrast
  const light = new THREE.DirectionalLight(0xffffff, 1.2); // Increased intensity
  light.position.set(0, 20, 30);
  offScene.add(light);

  // Add more lights for better definition
  const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
  fillLight.position.set(-20, 0, 20);
  offScene.add(fillLight);

  offScene.add(new THREE.AmbientLight(0xffffff, 0.4)); // Slightly brighter ambient

  // Slight head rotation
  headMesh.rotation.y = Math.PI / 6; // More pronounced angle

  // Render to a texture
  const renderTarget = new THREE.WebGLRenderTarget(offWidth, offHeight);
  offRenderer.setRenderTarget(renderTarget);
  offRenderer.render(offScene, offCamera);

  // Get pixels
  const pixels = new Uint8Array(offWidth * offHeight * 4);
  offRenderer.readRenderTargetPixels(renderTarget, 0, 0, offWidth, offHeight, pixels);

  // Convert to canvas
  const canvas = document.createElement('canvas');
  canvas.width = offWidth;
  canvas.height = offHeight;
  const ctx = canvas.getContext('2d');
  const imageData = ctx.createImageData(offWidth, offHeight);
  imageData.data.set(pixels);

  // Flip image (WebGL coordinate system is inverted)
  flipImageDataVertically(imageData, offWidth, offHeight);
  ctx.putImageData(imageData, 0, 0);

  // Get data URL
  const dataURL = canvas.toDataURL('image/png');
  faceIconCache[power] = dataURL;

  // Cleanup
  offRenderer.dispose();
  renderTarget.dispose();

  return dataURL;
}

// Add a subtle idle animation for faces
function idleAnimation(img) {
  if (img.dataset.animating === 'true') return;

  img.dataset.animating = 'true';

  const animation = img.animate([
    { transform: 'rotate(0deg) scale(1)' },
    { transform: 'rotate(-2deg) scale(0.98)' },
    { transform: 'rotate(0deg) scale(1)' }
  ], {
    duration: 1500,
    easing: 'ease-in-out'
  });

  animation.onfinish = () => {
    img.dataset.animating = 'false';
  };
}

// Helper to flip image data vertically
function flipImageDataVertically(imageData, width, height) {
  const bytesPerRow = width * 4;
  const temp = new Uint8ClampedArray(bytesPerRow);
  for (let y = 0; y < height / 2; y++) {
    const topOffset = y * bytesPerRow;
    const bottomOffset = (height - y - 1) * bytesPerRow;
    temp.set(imageData.data.slice(topOffset, topOffset + bytesPerRow));
    imageData.data.set(imageData.data.slice(bottomOffset, bottomOffset + bytesPerRow), topOffset);
    imageData.data.set(temp, bottomOffset);
  }
}

// --- NEW: Function to play a random sound effect ---
function playRandomSoundEffect() {
  // List all the sound snippet filenames in assets/sounds
  const soundEffects = [
    'snippet_2.mp3',
    'snippet_3.mp3',
    'snippet_4.mp3',
    'snippet_9.mp3',
    'snippet_10.mp3',
    'snippet_11.mp3',
    'snippet_12.mp3',
    'snippet_13.mp3',
    'snippet_14.mp3',
    'snippet_15.mp3',
    'snippet_16.mp3',
    'snippet_17.mp3',
  ];
  // Pick one at random
  const chosen = soundEffects[Math.floor(Math.random() * soundEffects.length)];

  // Create an <audio> and play
  const audio = new Audio(`./sounds/${chosen}`);
  audio.volume = 0.5; // Set volume to 50% to avoid being too loud

  if (config.isDebugMode || config.isTestingMode) {
    console.debug("Not playing sounds in debug or testing mode");
    return;
  }

  console.log(`Attempting to play sound: ${chosen}`);

  // Try to play the audio
  const playPromise = audio.play();

  if (playPromise !== undefined) {
    playPromise
      .then(() => {
        console.log(`Successfully played sound: ${chosen}`);
      })
      .catch(err => {
        console.error(`Failed to play sound ${chosen}:`, err);
        console.log('This might be due to browser autoplay policies. User interaction may be required.');
      });
  }
}
