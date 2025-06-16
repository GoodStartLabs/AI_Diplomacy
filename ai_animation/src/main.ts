import * as THREE from "three";
import "./style.css"
import { initMap } from "./map/create";
import { gameState } from "./gameState";
import { loadBtn, prevBtn, nextBtn, speedSelector, fileInput, playBtn, mapView, loadGameBtnFunction } from "./domElements";
import { config } from "./config";
import { Tween, Group, Easing } from "@tweenjs/tween.js";
import { initRotatingDisplay, } from "./components/rotatingDisplay";
import { debugMenuInstance } from "./debug/debugMenu";
import { initializeBackgroundAudio, startBackgroundAudio } from "./backgroundAudio";
import { updateLeaderboard } from "./components/leaderboard";
import { _setPhase, nextPhase, previousPhase } from "./phase";
import { togglePlayback } from "./phase";

//TODO: Create a function that finds a suitable unit location within a given polygon, for placing units better 
//  Currently the location for label, unit, and SC are all the same manually picked location

const isStreamingMode = import.meta.env.VITE_STREAMING_MODE
const phaseStartIdx = undefined;

// Panic flag to stop execution when critical errors occur
let hasPanicked = false;

// --- INITIALIZE SCENE ---
function initScene() {
  gameState.createThreeScene()

  initializeBackgroundAudio()


  // Initialize standings board
  // TODO: Re-add standinds board when it has an actual use, and not stale data
  //
  //initStandingsBoard();


  // Load coordinate data, then build the map
  gameState.loadBoardState().then(() => {
    initMap(gameState.scene).then(() => {

      // Initialize rotating display
      initRotatingDisplay();

      gameState.cameraPanAnim = createCameraPan()

      gameState.loadGameFile().then(() => {

        // Update info panel with initial power information
        updateLeaderboard();

        if (phaseStartIdx !== undefined) {
          gameState.eventQueue.start();
          gameState.eventQueue.scheduleDelay(500, () => {
            _setPhase(phaseStartIdx)
          }, `phase-start-delay-${Date.now()}`)
        } else if (!isStreamingMode && !config.isTestingMode) {
          // Auto-start playback for normal mode (not streaming, no specific phase, not testing)
          // Note: Background audio will start when togglePlayback is called (which provides user interaction context)
          gameState.eventQueue.start();
          gameState.eventQueue.scheduleDelay(1000, () => {
            console.log("Auto-starting playback after game load");
            togglePlayback(true); // true = explicitly set to playing
          }, `auto-start-playback-${Date.now()}`);
        }
      })


      // Initialize debug menu if in debug mode
      if (config.isDebugMode) {
        debugMenuInstance.show();
      }
      if (isStreamingMode) {
        startBackgroundAudio()
        gameState.eventQueue.start();
        gameState.eventQueue.scheduleDelay(2000, () => {
          togglePlayback()
        }, `streaming-mode-start-${Date.now()}`)
      }
    })
  }).catch(err => {
    // Use console.error instead of logger.log to avoid updating the info panel
    console.error(`Error loading coords: ${err.message}`);
  });

  // Handle resizing
  window.addEventListener('resize', onWindowResize);

  // Kick off animation loop
  animate();
}

function createCameraPan(): Group {
  // Create a target object to store the desired camera position
  const cameraStart = { x: gameState.camera.position.x, y: gameState.camera.position.y, z: gameState.camera.position.z };

  // Move from the starting camera position to the left side of the map
  let moveToStartSweepAnim = new Tween(cameraStart).to({
    x: -400,
    y: 500,
    z: 1000
  }, 8000).onUpdate((target) => {
    // Use smooth interpolation to avoid jumps
    gameState.camera.position.lerp(new THREE.Vector3(target.x, target.y, target.z), 0.1);
  });

  let cameraSweepOperation = new Tween({ timeStep: 0 })
    .to({
      timeStep: Math.PI
    }, 20000)
    .onUpdate((tweenObj) => {
      let radius = 2200;
      // Calculate the target position
      const targetX = radius * Math.sin(tweenObj.timeStep / 2) - 400;
      const targetY = 500 + 200 * Math.sin(tweenObj.timeStep);
      const targetZ = 1000 + 900 * Math.sin(tweenObj.timeStep);

      gameState.camera.position.set(targetX, targetY, targetZ);
    })
    .easing(Easing.Quadratic.InOut).yoyo(true).repeat(Infinity);

  moveToStartSweepAnim.chain(cameraSweepOperation);
  moveToStartSweepAnim.start();
  return new Group(moveToStartSweepAnim, cameraSweepOperation);
}

function updateAnimations() {

  // Check if all animations are complete
  if (gameState.unitAnimations.length > 0) {
    // Filter out completed animations
    gameState.unitAnimations = gameState.unitAnimations.filter(anim => anim.isPlaying());
    // Call update on each active animation
    gameState.unitAnimations.forEach((anim) => anim.update())
  }

  // Update any pulsing or wave animations on supply centers or units
  if (gameState.scene.userData.animatedObjects) {
    gameState.scene.userData.animatedObjects.forEach(obj => {
      if (obj.userData.pulseAnimation) {
        const anim = obj.userData.pulseAnimation;
        anim.time += anim.speed;
        if (obj.userData.glowMesh) {
          const pulseValue = Math.sin(anim.time) * anim.intensity + 0.5;
          obj.userData.glowMesh.material.opacity = 0.2 + (pulseValue * 0.3);
          obj.userData.glowMesh.scale.set(
            1 + (pulseValue * 0.1),
            1 + (pulseValue * 0.1),
            1 + (pulseValue * 0.1)
          );
        }
        // Subtle bobbing up/down
        obj.position.y = 2 + Math.sin(anim.time) * 0.5;
      }
    });
  }
}
// --- ANIMATION LOOP ---
/*
 * Main animation loop that runs continuously
 * Handles camera movement, animations, and game state transitions
 */
function animate() {
  if (hasPanicked) return; // Stop the loop if we've panicked
  
  try {
    // All things that aren't ThreeJS items happen in the eventQueue. The queue if filled with the first phase before the animate is kicked off, then all subsequent events are updated when other events finish. F
    // For instance, when the messages finish playing, they should kick off the check to see if we should advance turns.
    gameState.eventQueue.update();
  } catch (error) {
    console.error('CRITICAL ERROR - STOPPING EXECUTION:', error);
    hasPanicked = true;
    return; // Exit without scheduling next frame
  }
  
  requestAnimationFrame(animate);

  if (gameState.isPlaying) {
    // Update the camera angle
    // FIXME: This has to call the update functino twice inorder to avoid a bug in Tween.js, see here  https://github.com/tweenjs/tween.js/issues/677
    gameState.cameraPanAnim.update();
    gameState.cameraPanAnim.update();

  }

  updateAnimations()
  gameState.camControls.update();
  gameState.renderer.render(gameState.scene, gameState.camera);
}


// --- RESIZE HANDLER ---
function onWindowResize() {
  gameState.camera.aspect = mapView.clientWidth / mapView.clientHeight;
  gameState.camera.updateProjectionMatrix();
  gameState.renderer.setSize(mapView.clientWidth, mapView.clientHeight);
}







// --- EVENT HANDLERS ---
loadBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (file) {
    loadGameBtnFunction(file);
  }
});

prevBtn.addEventListener('click', () => {
  previousPhase()
});
nextBtn.addEventListener('click', () => {
  // FIXME: Need to have this wait until all animations are complete, trying to click next when still animating results in not finding units where they should be.
  nextPhase()
});

playBtn.addEventListener('click', () => {
  // Ensure background audio is ready when user manually clicks play
  startBackgroundAudio();
  togglePlayback();
});

speedSelector.addEventListener('change', e => {
  config.playbackSpeed = parseInt(e.target.value);
  // If we're currently playing, restart the event queue with the new speed
  if (gameState.isPlaying) {
    // Reset and restart event queue to pick up new speed
    gameState.eventQueue.reset();
    gameState.eventQueue.start();
    gameState.nextPhaseScheduled = true;
    gameState.eventQueue.scheduleDelay(config.effectivePlaybackSpeed, () => {
      try {
        advanceToNextPhase()
      } catch {
        nextPhase()
      }
    }, `speed-change-next-phase-${Date.now()}`);
  }
});


// --- BOOTSTRAP ON PAGE LOAD ---
window.addEventListener('load', initScene);




