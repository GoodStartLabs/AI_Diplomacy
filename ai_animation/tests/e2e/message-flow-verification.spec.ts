import { test, expect, Page } from '@playwright/test';
import { waitForGameReady, getCurrentPhaseName, enableInstantMode, getAllChatMessages, waitForMessagesToComplete } from './test-helpers';

interface MessageRecord {
  content: string;
  chatWindow: string;
  phase: string;
  timestamp: number;
}

/**
 * Gets expected messages for current power from the browser's game data
 */
async function getExpectedMessagesFromBrowser(page: Page): Promise<Array<{
  sender: string;
  recipient: string;
  message: string;
  phase: string;
}>> {
  return await page.evaluate(() => {
    const gameData = window.gameState?.gameData;
    const currentPower = window.gameState?.currentPower;
    
    if (!gameData || !currentPower) return [];
    
    const relevantMessages: Array<{
      sender: string;
      recipient: string;
      message: string;
      phase: string;
    }> = [];
    
    gameData.phases.forEach((phase: any) => {
      if (phase.messages) {
        phase.messages.forEach((msg: any) => {
          // Apply same filtering logic as updateChatWindows()
          if (msg.sender === currentPower || 
              msg.recipient === currentPower || 
              msg.recipient === 'GLOBAL') {
            relevantMessages.push({
              sender: msg.sender,
              recipient: msg.recipient,
              message: msg.message,
              phase: phase.name
            });
          }
        });
      }
    });
    
    return relevantMessages;
  });
}



test.describe('Message Flow Verification', () => {
  test('should verify basic message system functionality', async ({ page }) => {
    // This test verifies the message system works and doesn't get stuck
    await page.goto('http://localhost:5173');
    await waitForGameReady(page);
    
    // Enable instant mode for faster testing
    await enableInstantMode(page);
    
    // Verify game state is accessible
    const gameState = await page.evaluate(() => ({
      hasGameData: !!window.gameState?.gameData,
      currentPower: window.gameState?.currentPower,
      phaseIndex: window.gameState?.phaseIndex,
      hasEventQueue: !!window.gameState?.eventQueue
    }));
    
    expect(gameState.hasGameData).toBe(true);
    expect(gameState.currentPower).toBeTruthy();
    expect(gameState.hasEventQueue).toBe(true);
    
    console.log(`Game loaded with current power: ${gameState.currentPower}`);
    
    // Start playback for a short time to verify message system works
    await page.click('#play-btn');
    
    // Monitor for basic functionality over 10 seconds
    let messageAnimationDetected = false;
    let eventQueueActive = false;
    
    for (let i = 0; i < 100; i++) { // 10 seconds in 100ms intervals
      const status = await page.evaluate(() => ({
        isAnimating: window.gameState?.messagesPlaying || false,
        hasEvents: window.gameState?.eventQueue?.pendingEvents?.length > 0 || false,
        phase: document.querySelector('#phase-display')?.textContent?.replace('Era: ', '') || ''
      }));
      
      if (status.isAnimating) {
        messageAnimationDetected = true;
      }
      
      if (status.hasEvents) {
        eventQueueActive = true;
      }
      
      // If we've detected both, we can finish early
      if (messageAnimationDetected && eventQueueActive) {
        break;
      }
      
      await page.waitForTimeout(100);
    }
    
    // Stop playback
    await page.click('#play-btn');
    
    // Verify basic functionality was detected
    console.log(`Message animation detected: ${messageAnimationDetected}`);
    console.log(`Event queue active: ${eventQueueActive}`);
    
    // At minimum, the event queue should be active (even if no messages in first phase)
    expect(eventQueueActive).toBe(true);
    
    console.log('✅ Basic message system functionality verified');
  });
  
  test('should verify no simultaneous message animations', async ({ page }) => {
    await page.goto('http://localhost:5173');
    await waitForGameReady(page);
    
    // Enable instant mode for faster testing
    await enableInstantMode(page);
    
    let simultaneousAnimationDetected = false;
    let animationCount = 0;
    
    // Start playback
    await page.click('#play-btn');
    
    // Monitor animation state for overlaps
    for (let i = 0; i < 100; i++) { // 10 seconds
      const animationStatus = await page.evaluate(() => {
        // Check if multiple animation systems are active simultaneously
        const messagesPlaying = window.gameState?.messagesPlaying || false;
        const chatMessages = document.querySelectorAll('.chat-message');
        const recentlyAdded = Array.from(chatMessages).filter(msg => {
          const timeStamp = msg.dataset.timestamp;
          return timeStamp && (Date.now() - parseInt(timeStamp)) < 500; // Added in last 500ms
        });
        
        return {
          messagesPlaying,
          messageCount: chatMessages.length,
          recentMessages: recentlyAdded.length
        };
      });
      
      if (animationStatus.messagesPlaying) {
        animationCount++;
        
        // Check if too many messages appear simultaneously (could indicate race condition)
        if (animationStatus.recentMessages > 3) {
          simultaneousAnimationDetected = true;
          console.warn(`Potential simultaneous animation: ${animationStatus.recentMessages} recent messages`);
        }
      }
      
      await page.waitForTimeout(100);
    }
    
    // Stop playback
    await page.click('#play-btn');
    
    console.log(`Animation cycles detected: ${animationCount}`);
    console.log(`Simultaneous animations detected: ${simultaneousAnimationDetected}`);
    
    // We should see some animations but no simultaneous ones
    expect(simultaneousAnimationDetected).toBe(false);
    
    console.log('✅ No simultaneous message animations detected');
  });
});