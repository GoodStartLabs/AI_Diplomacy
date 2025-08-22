import * as THREE from "three";
import { Tween, Easing } from "@tweenjs/tween.js";
import { createUnitMesh } from "./create";
import { getProvincePosition } from "../map/utils";
import { gameState } from "../gameState";
import type { UnitOrder } from "../types/unitOrders";
import { logger } from "../logger";
import { config } from "../config"; // Assuming config is defined in a separate file
import { PowerENUM, ProvinceENUM } from "../types/map";
import { UnitTypeENUM } from "../types/units";
import { sineWave, getTimeInSeconds } from "../utils/timing";
import { ScheduledEvent } from "../events";
import { GamePhase } from "../types/gameState";
//import { color } from "chart.js/helpers";
//import { depth } from "three/tsl";


function buildFancyArrow(length: number, colorDeter: string): THREE.Mesh {
  //Specs to change arrow size
  const tw = 3.5;
  const headLength = tw * 4;
  const hw = tw * 4;

  const shape = new THREE.Shape()
    .moveTo(0, tw / 2)
    .lineTo(length - headLength, tw / 2)
    .lineTo(length - headLength, hw / 2)
    .lineTo(length, 0)
    .lineTo(length - headLength, -hw / 2)
    .lineTo(length - headLength, -tw / 2)
    .lineTo(0, -tw / 2)
    .closePath();

  const extrude = new THREE.ExtrudeGeometry(shape, { depth: 1 })
  let mat: THREE.Material;

  if (colorDeter == 'Move') {
    mat = new THREE.MeshStandardMaterial({ color: 0x00FF00 })
  } else if (colorDeter == 'Bounce') {
    mat = new THREE.MeshStandardMaterial({ color: 0xFF0000 })
  }
  const mesh = new THREE.Mesh(extrude, mat)
  //(Potential Addition: Outline of arrow)
  return mesh;
}

function createShield() {

  //Shield Specs
  const BSH = 10
  const SW = 10
  const TSH = 10


  const outL = new THREE.Shape()
    .moveTo(0, TSH)
    .lineTo(SW, TSH)
    .lineTo(SW, 0)
    .quadraticCurveTo(SW, -BSH, 0, -BSH)
    .quadraticCurveTo(-SW, -BSH, -SW, 0)
    .lineTo(-SW, TSH)
    .lineTo(0, TSH)
    .closePath();

  const SExtrude = new THREE.ExtrudeGeometry(outL, { depth: 5 })

  const SMat = new THREE.MeshStandardMaterial({ color: 0x00FF00 })

  const SMesh = new THREE.Mesh(SExtrude, SMat)

  return SMesh

}

function getUnit(unitOrder: UnitOrder, power: string) {
  if (power === undefined) throw new Error("Must pass the power argument, cannot be undefined")
  let posUnits = gameState.unitMeshes.filter((unit) => {
    return (
      unit.userData.province === unitOrder.unit.origin &&
      unit.userData.type === unitOrder.unit.type &&
      unit.userData.power === power &&
      (unit.userData.isAnimating === false || unit.userData.isAnimating === undefined)
    );
  });

  if (posUnits.length === 0) {
    return -1;
  }

  // Return the first matching unit
  return gameState.unitMeshes.indexOf(posUnits[0]);
}

/* Return a tween animation for the spawning of a unit.
 *  Intended to be invoked before the unit is added to the scene
*/
function createSpawnAnimation(newUnitMesh: THREE.Group): Tween {
  // Start the unit really high, and lower it to the board.
  newUnitMesh.position.setY(1000)
  return new Tween({ y: 1000 })
    .to({ y: 10 }, config.effectiveAnimationDuration || 1000)
    .easing(Easing.Quadratic.Out)
    .onUpdate((object) => {
      newUnitMesh.position.setY(object.y)
    }).start()
}

function createMoveAnimation(unitMesh: THREE.Group, orderDestination: ProvinceENUM): Tween {
  let destinationVector = getProvincePosition(orderDestination);
  if (!destinationVector) {
    throw new Error("Unable to find the vector for province with name " + orderDestination)
  }
  unitMesh.userData.province = orderDestination;
  unitMesh.userData.isAnimating = true

  // Store animation start time for consistent wave motion
  const animStartTime = getTimeInSeconds();

  const start = new THREE.Vector3();
  //prevents the arrow mesh from using local coords which mess with the alignment 
  unitMesh.getWorldPosition(start);
  const end = getProvincePosition(orderDestination)!;
  //lines to determine direction and length of the arrow, minus a little from the length so it's offset 
  const direct = new THREE.Vector3().subVectors(end, start);
  const length = Math.max(direct.length() - 2, 0);
  const arrowMesh = buildFancyArrow(length, 'Move');
  const dir = direct.clone().normalize();

  arrowMesh.position.copy(start);

  //Core of the arrow alignment, won't work without this
  const q = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(1, 0, 0), dir
  );
  arrowMesh.setRotationFromQuaternion(q);

  arrowMesh.scale.set(0, 1, 1);

  gameState.scene.add(arrowMesh);
  unitMesh.userData.moveArrow = arrowMesh;
  //Value beside x:1 controls the speed of the growth
  const ArrowGrow = new Tween(arrowMesh.scale)
    .to({ x: 1 }, 1000)
    .easing(Easing.Quadratic.Out)
    .onComplete(() => {
      const anim = new Tween(unitMesh.position)
        .to({
          x: destinationVector.x,
          y: 10,
          z: destinationVector.z
        }, config.effectiveAnimationDuration)
        .easing(Easing.Quadratic.InOut)
        .onUpdate(() => {
          // Use elapsed time from animation start for consistent wave motion
          const elapsedTime = getTimeInSeconds() - animStartTime;
          unitMesh.position.y = 10 + sineWave(config.animation.unitBobFrequency, elapsedTime, 2); // 2 units amplitude
          if (unitMesh.userData.type === 'F') {
            unitMesh.rotation.z = sineWave(config.animation.fleetRollFrequency, elapsedTime, 0.1);
            unitMesh.rotation.x = sineWave(config.animation.fleetPitchFrequency, elapsedTime, 0.1);
          }
        })
        .onComplete(() => {
          unitMesh.position.y = 10;
          if (unitMesh.userData.type === 'F') {
            unitMesh.rotation.z = 0;
            unitMesh.rotation.x = 0;
          }
          gameState.scene.remove(arrowMesh);
          delete unitMesh.userData.moveArrow;
          unitMesh.userData.isAnimating = false
        })
        .start();
      gameState.unitAnimations.push(anim);
    })
    .start()
  gameState.unitAnimations.push(ArrowGrow)
  return ArrowGrow
}

//Animation for bounce

function createBounceAnimation(unitMesh: THREE.Group, attemptedDestination: ProvinceENUM): Tween {
  const end = getProvincePosition(attemptedDestination)!;
  if (!end) throw new Error(`No position found for attempted destination: ${attemptedDestination}`);

  unitMesh.userData.isAnimating = true;


  const start = new THREE.Vector3();
  //prevents the arrow mesh from using local coords which mess with the alignment 
  unitMesh.getWorldPosition(start);
  //lines to determine direction and length of the arrow, minus a little from the length so it's offset 
  const direct = new THREE.Vector3().subVectors(end, start);
  const length = Math.max(direct.length() - 2, 0);
  const arrowMesh = buildFancyArrow(length, 'Bounce');
  const dir = direct.clone().normalize();

  arrowMesh.position.copy(start);

  //Core of the arrow alignment, won't work without this
  const q = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(1, 0, 0), dir
  );
  arrowMesh.setRotationFromQuaternion(q);

  arrowMesh.scale.set(0, 1, 1);

  gameState.scene.add(arrowMesh);
  unitMesh.userData.moveArrow = arrowMesh;
  const growBounce = new Tween(arrowMesh.scale)
    //Number beside x:1 controls speed in ms
    .to({ x: 1 }, 1000)
    .easing(Easing.Quadratic.Out)
    .onComplete(() => {
      const bounceOut = new Tween(unitMesh.position)
        .to({ x: end.x, y: 10, z: end.z }, config.effectiveAnimationDuration / 2)
        .easing(Easing.Quadratic.Out)
        .repeat(1)
        .yoyo(true)
        .onComplete(() => {
          if (unitMesh.userData.moveArrow) {
            gameState.scene.remove(arrowMesh);
            delete unitMesh.userData.moveArrow;
            unitMesh.userData.isAnimating = false
          }
        });

      bounceOut.start();

      gameState.unitAnimations.push(bounceOut);
    })
  growBounce.start()
  gameState.unitAnimations.push(growBounce)
  return growBounce;
}


function createHoldAnimation(unitMesh: THREE.Group): Tween {
  // 1) Build the shield mesh
  const shield = createShield();

  // 2) Figure out where the unit’s feet are
  const worldPos = new THREE.Vector3();
  unitMesh.getWorldPosition(worldPos);

  shield.position.set(worldPos.x, 16, worldPos.z + 8);
  shield.scale.set(1, 0, 1);           // collapse height

  gameState.scene.add(shield);
  unitMesh.userData.newshield = shield;
  unitMesh.userData.isAnimating = true;

  const growTween = new Tween(shield.scale)
    .to({ x: 1, y: 1, z: 1 }, 2000)
    .easing(Easing.Quadratic.Out)
    .onComplete(() => {
      gameState.scene.remove(shield);
      unitMesh.userData.isAnimating = false;
    })
    .start();

  gameState.unitAnimations.push(growTween);

  return growTween;
}

export function createAnimateUnitsEvent(phase: GamePhase, phaseIdx: number): ScheduledEvent {
  return new ScheduledEvent(`createAnimations-${phase.name}`, () => createAnimationsForNextPhase(phaseIdx))
}

/**
 * Creates animations for unit movements based on orders from the previous phase
 *
**/
export function createAnimationsForNextPhase(phaseIdx: number) {
  if (phaseIdx === 0) { throw new Error("Cannot create animations for phase 0, must start on 1 or higher") }
  let previousPhase = gameState.gameData?.phases[phaseIdx - 1]
  // const sequence = ["build", "disband", "hold", "move", "bounce", "retreat"]
  // Safety check - if no previous phase or no orders, return
  if (!previousPhase) {
    logger.log("No previous phase to animate");
    return;
  }
  for (const [power, orders] of Object.entries(previousPhase.orders)) {
    if (orders === null) {
      continue
    }
    for (const order of orders) {
      // Check if unit bounced
      // With new format: {A: {"BUD": [results]}, F: {"BUD": [results]}}
      const unitType = order.unit.type;
      const unitOrigin = order.unit.origin;

      let result = undefined;
      if (previousPhase.results && previousPhase.results[unitType] && previousPhase.results[unitType][unitOrigin]) {
        const resultArray = previousPhase.results[unitType][unitOrigin];
        result = resultArray.length > 0 ? resultArray[0] : null;

      }

      if (result === undefined) {
        throw new Error(`No result present in current phase for previous phase order: ${unitType} ${unitOrigin}. Cannot continue`);
      }

      if (result === "bounce") {
        order.type = "bounce"
      }
      // If the result is void, that means the move was not valid?
      if (result === "void" || result === "no convoy") continue;
      let unitIndex = -1

      unitIndex = getUnit(order, power);
      switch (order.type) {
        case "move":
          if (!order.destination) throw new Error("Move order with no destination, cannot complete move.")
          if (unitIndex < 0) throw new Error("Unable to find unit for order " + order.raw)
          // Create a tween for smooth movement
          createMoveAnimation(gameState.unitMeshes[unitIndex], order.destination as keyof typeof ProvinceENUM)
          break;

        case "disband":
          // TODO: Death animation
          if (unitIndex < 0) throw new Error("Unable to find unit for order " + order.raw)
          gameState.scene.remove(gameState.unitMeshes[unitIndex]);
          gameState.unitMeshes.splice(unitIndex, 1);
          break;

        case "build":
          // TODO: Spawn animation?
          let newUnit = createUnitMesh({
            power: PowerENUM[power as keyof typeof PowerENUM],
            type: UnitTypeENUM[order.unit.type as keyof typeof UnitTypeENUM],
            province: order.unit.origin
          })
          gameState.unitAnimations.push(createSpawnAnimation(newUnit))
          gameState.scene.add(newUnit)
          gameState.unitMeshes.push(newUnit)
          break;

        case "bounce":
          if (unitIndex < 0) throw new Error("Unable to find unit for order " + order.raw)
          if (!order.destination) throw new Error("Bounce order without destination")
          createBounceAnimation(gameState.unitMeshes[unitIndex], order.destination as ProvinceENUM);
          break;

        case "hold":
          //TODO: Hold animation, maybe a sheild or something?
          createHoldAnimation(gameState.unitMeshes[unitIndex])
          break;

        case "convoy":
          // The unit doesn't move, so no animation for now
          break;

        case "retreat":
          if (unitIndex < 0) throw new Error("Unable to find unit for order " + order.raw)
          createMoveAnimation(gameState.unitMeshes[unitIndex], order.destination as keyof typeof ProvinceENUM)
          break;

        case "support":
          break

        default:
          // FIXME: There is an issue where some F are not getting disbanded when I believe they should
          //    check ROM in game 0, turn 2-5.  
          throw new Error(`Unhandled order.type ${order.type}.`)
      }
    }
  }
}
