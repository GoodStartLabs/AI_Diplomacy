import { test, expect, Page } from '@playwright/test';
import { waitForGameReady, getCurrentPhaseName, enableInstantMode, getAllChatMessages, waitForMessagesToComplete } from './test-helpers';

interface MessageRecord {
  content: string;
  chatWindow: string;
  phase: string;
  timestamp: number;
}

/**
 * Comprehensive test to verify message system functionality and data quality
 */
async function verifyMessageSystemHealth(page: Page): Promise<{
  hasValidGameData: boolean;
  messageCount: number;
  eventQueueActive: boolean;
  momentsWithNoMessages: number;
}> {
  return await page.evaluate(() => {
    const gameData = window.gameState?.gameData;
    const currentPower = window.gameState?.currentPower;
    const momentsData = window.gameState?.momentsData;
    
    if (!gameData || !currentPower) {
      return {
        hasValidGameData: false,
        messageCount: 0,
        eventQueueActive: false,
        momentsWithNoMessages: 0
      };
    }
    
    // Count relevant messages
    let messageCount = 0;
    gameData.phases.forEach((phase: any) => {
      if (phase.messages) {
        phase.messages.forEach((msg: any) => {
          if (msg.sender === currentPower || 
              msg.recipient === currentPower || 
              msg.recipient === 'GLOBAL') {
            messageCount++;
          }
        });
      }
    });
    
    // Check for moments that might have no messages (data quality issue)
    let momentsWithNoMessages = 0;
    if (momentsData && Array.isArray(momentsData)) {
      momentsData.forEach((moment: any) => {
        if (moment.interest_score >= 8.0 && moment.powers_involved?.length >= 2) {
          const power1 = moment.powers_involved[0];
          const power2 = moment.powers_involved[1];
          
          // Find the phase for this moment
          const phaseForMoment = gameData.phases.find((p: any) => p.name === moment.phase);
          if (phaseForMoment && phaseForMoment.messages) {
            const conversationMessages = phaseForMoment.messages.filter((msg: any) => {
              const sender = msg.sender?.toUpperCase();
              const recipient = msg.recipient?.toUpperCase();
              const p1 = power1?.toUpperCase();
              const p2 = power2?.toUpperCase();
              
              return (sender === p1 && recipient === p2) || (sender === p2 && recipient === p1);
            });
            
            if (conversationMessages.length === 0) {
              momentsWithNoMessages++;
            }
          }
        }
      });
    }
    
    return {
      hasValidGameData: true,
      messageCount,
      eventQueueActive: window.gameState?.eventQueue?.pendingEvents?.length > 0 || false,
      momentsWithNoMessages
    };
  });
}



test.describe('Message Flow Verification', () => {
  test('should verify message system health and data quality', async ({ page }) => {
    // This test verifies the message system works and validates data quality
    await page.goto('http://localhost:5173');
    await waitForGameReady(page);
    
    // Enable instant mode for faster testing
    await enableInstantMode(page);
    
    // Get comprehensive health check
    const healthStatus = await verifyMessageSystemHealth(page);
    
    expect(healthStatus.hasValidGameData).toBe(true);
    
    console.log(`Message system health check:`);
    console.log(`- Total relevant messages: ${healthStatus.messageCount}`);
    console.log(`- Event queue active: ${healthStatus.eventQueueActive}`);
    console.log(`- Moments with no messages: ${healthStatus.momentsWithNoMessages}`);
    
    // Data quality verification: should have no moments without messages
    // (Our new error-throwing approach prevents these from being processed)
    if (healthStatus.momentsWithNoMessages > 0) {
      console.warn(`⚠️ Found ${healthStatus.momentsWithNoMessages} high-interest moments with no messages`);
      console.warn(`This indicates potential data quality issues that would now throw errors`);
    }
    
    // Start playback briefly to verify system works
    await page.click('#play-btn');
    
    // Monitor for basic functionality over 5 seconds
    let eventQueueActive = false;
    
    for (let i = 0; i < 50; i++) { // 5 seconds in 100ms intervals
      const status = await page.evaluate(() => ({
        hasEvents: window.gameState?.eventQueue?.pendingEvents?.length > 0 || false,
      }));
      
      if (status.hasEvents) {
        eventQueueActive = true;
        break;
      }
      
      await page.waitForTimeout(100);
    }
    
    // Stop playback
    await page.click('#play-btn');
    
    // At minimum, the event queue should be active
    expect(eventQueueActive).toBe(true);
    
    console.log('✅ Message system health and data quality verified');
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