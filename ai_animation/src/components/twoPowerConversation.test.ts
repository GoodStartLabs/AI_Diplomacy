import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock Three.js and complex dependencies first
vi.mock('three', () => ({
  WebGLRenderer: vi.fn(),
  Scene: vi.fn(),
  PerspectiveCamera: vi.fn(),
  DirectionalLight: vi.fn(),
  AmbientLight: vi.fn(),
  BoxGeometry: vi.fn(),
  MeshStandardMaterial: vi.fn(),
  MeshBasicMaterial: vi.fn(),
  Mesh: vi.fn(),
  WebGLRenderTarget: vi.fn(),
}));

vi.mock('three/examples/jsm/Addons.js', () => ({
  OrbitControls: vi.fn()
}));

vi.mock('@tweenjs/tween.js', () => ({
  Tween: vi.fn(),
  Group: vi.fn()
}));

// Mock gameState with minimal implementation
vi.mock('../gameState', () => {
  const mockEventQueue = {
    pendingEvents: [],
    scheduleDelay: vi.fn(),
    reset: vi.fn(),
    start: vi.fn(),
    stop: vi.fn()
  };
  
  return {
    gameState: {
      isPlaying: false,
      isDisplayingMoment: false,
      phaseIndex: 0,
      gameData: {
        phases: [{
          name: 'S1901M',
          messages: []
        }]
      },
      eventQueue: mockEventQueue
    }
  };
});

// Mock config
vi.mock('../config', () => ({
  config: {
    conversationModalDelay: 500,
    conversationMessageDisplay: 1000,
    conversationMessageAnimation: 300,
    conversationFinalDelay: 2000
  }
}));

// Mock utils
vi.mock('../utils/powerNames', () => ({
  getPowerDisplayName: vi.fn(power => power)
}));

// Mock the phase module to avoid circular dependency
const mockSetPhase = vi.fn();
vi.mock('../phase', () => ({
  _setPhase: mockSetPhase
}));

// Setup minimal DOM mocks
Object.defineProperty(global, 'document', {
  value: {
    createElement: vi.fn(() => ({
      style: {},
      appendChild: vi.fn(),
      addEventListener: vi.fn(),
      querySelector: vi.fn(() => null),
      parentNode: { removeChild: vi.fn() },
      classList: { add: vi.fn() },
      textContent: '',
      id: ''
    })),
    getElementById: vi.fn(() => null),
    body: { appendChild: vi.fn() },
    removeEventListener: vi.fn(),
    addEventListener: vi.fn()
  }
});

// Import after all mocking
import { showTwoPowerConversation, closeTwoPowerConversation } from './twoPowerConversation';

// Get direct reference to the mocked gameState
let gameState: any;

describe('twoPowerConversation', () => {
  beforeEach(async () => {
    // Get the mocked gameState
    const gameStateModule = await import('../gameState');
    gameState = gameStateModule.gameState;
    
    // Reset mocked game state
    gameState.isPlaying = false;
    gameState.isDisplayingMoment = false;
    gameState.phaseIndex = 0;
    gameState.gameData.phases[0].messages = [];
    
    // Reset all mocks
    vi.clearAllMocks();
    gameState.eventQueue.pendingEvents = [];
  });

  describe('showTwoPowerConversation', () => {
    it('should throw error when no messages found (indicates data quality issue)', () => {
      gameState.isPlaying = true;
      
      expect(() => {
        showTwoPowerConversation({
          power1: 'FRANCE',
          power2: 'GERMANY'
        });
      }).toThrow('High-interest moment detected between FRANCE and GERMANY but no messages found');
    });

    it('should throw error when empty messages array provided', () => {
      gameState.isPlaying = false;
      
      expect(() => {
        showTwoPowerConversation({
          power1: 'FRANCE', 
          power2: 'GERMANY',
          messages: []
        });
      }).toThrow('High-interest moment detected between FRANCE and GERMANY but no messages found');
    });

    it('should schedule phase advancement when messages exist and game is playing', () => {
      gameState.isPlaying = true;
      gameState.gameData.phases[0].messages = [
        { sender: 'FRANCE', recipient: 'GERMANY', message: 'Hello', time_sent: '1' }
      ];

      showTwoPowerConversation({
        power1: 'FRANCE',
        power2: 'GERMANY'
      });

      // Should have scheduled events in the queue
      expect(gameState.eventQueue.scheduleDelay).toHaveBeenCalled();
      
      // Should have marked as displaying moment
      expect(gameState.isDisplayingMoment).toBe(true);
    });
  });

  describe('Event queue safety', () => {
    it('should schedule events when messages exist', () => {
      gameState.isPlaying = true;
      gameState.gameData.phases[0].messages = [
        { sender: 'FRANCE', recipient: 'GERMANY', message: 'Test', time_sent: '1' }
      ];

      showTwoPowerConversation({
        power1: 'FRANCE',
        power2: 'GERMANY'
      });

      // Should have scheduled events in the queue
      expect(gameState.eventQueue.scheduleDelay).toHaveBeenCalled();
      
      // Should have marked as displaying moment
      expect(gameState.isDisplayingMoment).toBe(true);
    });

    it('should throw error for empty message arrays as they indicate data quality issues', () => {
      gameState.isPlaying = true;
      
      // Test with empty messages - should throw error
      expect(() => {
        showTwoPowerConversation({
          power1: 'FRANCE',
          power2: 'GERMANY',
          messages: []
        });
      }).toThrow('High-interest moment detected between FRANCE and GERMANY but no messages found');
    });
  });
});