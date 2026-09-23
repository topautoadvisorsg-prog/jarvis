import { TalkingHead } from "talkinghead";
import * as THREE from "three";

const container = document.getElementById("avatarStage");
const reactor = document.getElementById("reactorWrap");
const status = document.getElementById("avatarStatus");

let head = null;
let ready = false;
let mouthTimer = null;
let mouthLevel = 0;
let previousSpectrumLevel = 0;
let audioAnalyser = null;
let analyserWave = null;
let analyserSpectrum = null;
let analyserFrame = null;
let lastAnalyserUpdate = 0;
let resolveReady;
const readyPromise = new Promise((resolve) => { resolveReady = resolve; });
let desiredGeneration = 0;
let activeGeneration = 0;
let interruptedGeneration = 0;
let streamOpen = false;
let streamStarting = false;
let pendingEnd = false;
let pendingPCM = [];
let playbackClockStart = 0;
let avatarClockStart = 0;
const hologramShaders = [];
let hologramState = 0;
let syntheticPortrait = null;

// Oculus visemes supported by TalkingHead / ARKit-compatible avatars.
// The frequency-band approach is adapted from three.ws LipSyncAnalyser
// (Apache-2.0): https://github.com/nirholas/three.ws/blob/main/src/lip-sync-analyser.js
const VISEMES = [
  "viseme_aa", "viseme_O", "viseme_U", "viseme_E", "viseme_I",
  "viseme_nn", "viseme_RR", "viseme_SS", "viseme_FF", "viseme_TH",
  "viseme_CH", "viseme_DD", "viseme_kk", "viseme_PP",
];
const visemeWeights = Object.fromEntries(VISEMES.map((name) => [name, 0]));

function showStatus(text, kind = "") {
  status.textContent = text;
  status.dataset.kind = kind;
}

function resetMouth(fast = false) {
  mouthLevel = 0;
  previousSpectrumLevel = 0;
  if (syntheticPortrait) {
    syntheticPortrait.style.height = "1px";
    syntheticPortrait.style.width = "9.5%";
    syntheticPortrait.style.boxShadow = "0 0 3px #12dfffb3";
    syntheticPortrait.style.setProperty("--mouth-line-opacity", ".82");
  }
  if (!head) return;
  for (const key of [...VISEMES, "jawOpen", "mouthOpen", "mouthPucker", "mouthFunnel"]) {
    if (key in visemeWeights) visemeWeights[key] = 0;
    try { head.setFixedValue(key, null, fast ? 25 : 100); } catch {}
  }
}

function averageBand(minHz, maxHz) {
  const nyquist = audioAnalyser.context.sampleRate / 2;
  const first = Math.max(1, Math.floor(minHz / nyquist * analyserSpectrum.length));
  const last = Math.min(analyserSpectrum.length - 1, Math.ceil(maxHz / nyquist * analyserSpectrum.length));
  let sum = 0;
  for (let i = first; i <= last; i++) sum += analyserSpectrum[i] / 255;
  return sum / Math.max(1, last - first + 1);
}

function driveMouthFromAnalyser(now) {
  analyserFrame = requestAnimationFrame(driveMouthFromAnalyser);
  if (!ready || !head || !audioAnalyser || now - lastAnalyserUpdate < 24) return;
  lastAnalyserUpdate = now;
  if (reactor.classList.contains("avatar-visualizing")) return;

  audioAnalyser.getFloatTimeDomainData(analyserWave);
  audioAnalyser.getByteFrequencyData(analyserSpectrum);
  let sumSquares = 0;
  for (let i = 0; i < analyserWave.length; i++) {
    sumSquares += analyserWave[i] * analyserWave[i];
  }
  const rms = Math.sqrt(sumSquares / Math.max(1, analyserWave.length));
  const low = averageBand(80, 500);
  const mid = averageBand(500, 2000);
  const high = averageBand(2000, 7800);
  const overall = (low + mid + high) / 3;
  // RMS reliably detects speech in the streamed PCM. Spectrum selects shapes.
  const voiced = Math.max(0, Math.min(1, (rms - 0.006) * 10.5));
  mouthLevel = voiced > mouthLevel
    ? mouthLevel * 0.68 + voiced * 0.32
    : mouthLevel * 0.78 + voiced * 0.22;

  const bandTotal = low + mid + high + 0.0001;
  const lowShare = low / bandTotal;
  const midShare = mid / bandTotal;
  const highShare = high / bandTotal;
  const closure = previousSpectrumLevel > 0.22 && voiced < previousSpectrumLevel * 0.48
    ? 0.32 : 0;
  previousSpectrumLevel = voiced;

  // Keep the face conversational. Multiple low weights make distinct phoneme
  // shapes without the full-open jaw and permanent pucker of the old mapper.
  const targets = Object.fromEntries(VISEMES.map((name) => [name, 0]));
  // Select one dominant family. Stacking every vowel together makes the MPFB
  // rig form the same round, exaggerated mouth on every syllable.
  if (highShare > 0.42) {
    targets.viseme_SS = mouthLevel * 0.17;
    targets.viseme_FF = mouthLevel * 0.045;
  } else if (midShare > 0.34) {
    targets.viseme_E = mouthLevel * 0.18;
    targets.viseme_I = mouthLevel * 0.045;
  } else {
    targets.viseme_aa = mouthLevel * 0.16;
    if (lowShare > 0.62) targets.viseme_O = mouthLevel * 0.04;
  }
  targets.viseme_nn = mouthLevel * 0.025;
  targets.viseme_PP = closure * 0.7;
  if (syntheticPortrait) {
    const open = Math.min(0.72, mouthLevel * 0.72);
    const wide = Math.max(-0.25, Math.min(1, (midShare - lowShare) * 2.4));
    syntheticPortrait.style.height = `${(1 + open * 10).toFixed(2)}px`;
    syntheticPortrait.style.width = `${(9.5 + wide * 1.2).toFixed(2)}%`;
    syntheticPortrait.style.boxShadow = `0 0 ${(3 + open * 8).toFixed(2)}px #12dfffb3`;
    syntheticPortrait.style.setProperty("--mouth-line-opacity", (0.82 - open * 0.42).toFixed(3));
  }
  try {
    for (const name of VISEMES) {
      const target = targets[name];
      const smoothing = target > visemeWeights[name] ? 0.30 : 0.20;
      visemeWeights[name] += (target - visemeWeights[name]) * smoothing;
      if (mouthLevel < 0.015) visemeWeights[name] *= 0.62;
      head.setFixedValue(name, Math.min(0.46, visemeWeights[name]), 32);
    }
    head.setFixedValue("jawOpen", Math.min(0.08, mouthLevel * 0.08), 32);
    head.setFixedValue("mouthOpen", 0, 32);
    head.setFixedValue("mouthFunnel", 0, 32);
    head.setFixedValue("mouthPucker", 0, 32);
  } catch {}
}

function bindAudioAnalyser(analyser) {
  audioAnalyser = analyser;
  audioAnalyser.smoothingTimeConstant = 0.65;
  analyserWave = new Float32Array(analyser.fftSize);
  analyserSpectrum = new Uint8Array(analyser.frequencyBinCount);
  if (!analyserFrame) analyserFrame = requestAnimationFrame(driveMouthFromAnalyser);
}

function emitAudioEvent(type, detail = {}) {
  window.dispatchEvent(new CustomEvent("jarvis-avatar-audio", {
    detail: { type, generation: activeGeneration, ...detail },
  }));
}

async function startStream({ sampleRate = 16000, generation }) {
  desiredGeneration = generation;
  pendingPCM = [];
  pendingEnd = false;
  streamStarting = true;
  await readyPromise;
  if (generation !== desiredGeneration || generation === interruptedGeneration) return false;
  if (streamOpen) head.streamInterrupt();
  streamOpen = false;
  await head.streamStart(
    {
      sampleRate,
      waitForAudioChunks: true,
      lipsyncType: "words",
      metrics: { enabled: true, intervalHz: 4 },
    },
    () => {
      playbackClockStart = head.audioCtx?.currentTime || 0;
      avatarClockStart = head.animClock || 0;
      emitAudioEvent("playback-started", { sampleRate });
    },
    () => {
      streamOpen = false;
      resetMouth(true);
      emitAudioEvent("playback-ended", { sampleRate });
    },
    null,
    (metrics) => emitAudioEvent("metrics", {
      sampleRate,
      playbackTime: Math.max(0, (head.audioCtx?.currentTime || 0) - playbackClockStart),
      avatarTime: Math.max(0, ((head.animClock || 0) - avatarClockStart) / 1000),
      ...metrics,
    }),
  );
  if (generation !== desiredGeneration || generation === interruptedGeneration) {
    head.streamInterrupt();
    streamStarting = false;
    return false;
  }
  activeGeneration = generation;
  interruptedGeneration = 0;
  streamOpen = true;
  streamStarting = false;
  bindAudioAnalyser(head.audioAnalyzerNode);
  for (const audio of pendingPCM) head.streamAudio({ audio });
  pendingPCM = [];
  if (pendingEnd) head.streamNotifyEnd();
  return true;
}

function pushPCM(audio, generation) {
  if (generation !== desiredGeneration || generation === interruptedGeneration) return false;
  if (!streamOpen || streamStarting) {
    pendingPCM.push(audio);
    return true;
  }
  head.streamAudio({ audio });
  return true;
}

function endStream(generation) {
  if (generation !== desiredGeneration || generation === interruptedGeneration) return false;
  pendingEnd = true;
  if (streamOpen && !streamStarting) head.streamNotifyEnd();
  return true;
}

function setState(next) {
  reactor.dataset.avatarState = next || "standby";
  hologramState = ({ listening: 1, thinking: 2, tool: 3, speaking: 4 })[next] || 0;
  for (const shader of hologramShaders) shader.uniforms.jarvisState.value = hologramState;
  if (!ready || !head) return;
  try {
    if (next === "listening") {
      head.setFixedValue("eyeWideLeft", 0.12, 160);
      head.setFixedValue("eyeWideRight", 0.12, 160);
      head.setFixedValue("browInnerUp", 0.08, 160);
    } else if (next === "thinking") {
      head.setFixedValue("eyeWideLeft", null, 140);
      head.setFixedValue("eyeWideRight", null, 140);
      head.setFixedValue("browInnerUp", 0.22, 180);
      head.setFixedValue("eyesRotateY", 0.28, 220);
    } else if (next === "tool") {
      head.setFixedValue("browInnerUp", 0.3, 120);
      head.setFixedValue("eyesRotateY", -0.18, 160);
    } else {
      for (const key of ["eyeWideLeft", "eyeWideRight", "browInnerUp", "eyesRotateY"]) {
        head.setFixedValue(key, null, 180);
      }
    }
    if (next !== "speaking") resetMouth();
  } catch {}
}

function interrupt(generation = desiredGeneration) {
  if (!generation || interruptedGeneration === generation) return false;
  interruptedGeneration = generation;
  desiredGeneration = generation;
  pendingPCM = [];
  pendingEnd = false;
  clearTimeout(mouthTimer);
  mouthLevel = 0;
  if (head) {
    for (const key of [...VISEMES, "jawOpen", "mouthOpen", "mouthPucker", "mouthFunnel"]) {
      if (key in visemeWeights) visemeWeights[key] = 0;
      try { head.setFixedValue(key, 0, 18); } catch {}
    }
    mouthTimer = setTimeout(() => resetMouth(true), 240);
  }
  if (streamOpen || streamStarting) {
    try { head?.streamInterrupt?.(); } catch {}
  }
  streamOpen = false;
  streamStarting = false;
  emitAudioEvent("interrupted");
  return true;
}

function setVisualization(active) {
  reactor.classList.toggle("avatar-visualizing", Boolean(active));
}

function mountSyntheticPortrait() {
  if (document.getElementById("syntheticPortrait")) return;
  const portrait = document.createElement("div");
  portrait.id = "syntheticPortrait";
  portrait.innerHTML = `
    <img alt="Synthetic cyan JARVIS face" src="./assets/synthetic-face-v1.png">
    <div id="syntheticEyePulse"></div>
    <div id="syntheticMouth" aria-hidden="true"></div>`;
  syntheticPortrait = portrait.querySelector("#syntheticMouth");
  const image = portrait.querySelector("img");
  image.addEventListener("load", () => container.classList.add("synthetic-mounted"), { once: true });
  image.addEventListener("error", () => portrait.remove(), { once: true });
  container.appendChild(portrait);
}

window.JarvisAvatar = {
  get ready() { return ready; },
  bindAudioAnalyser,
  startStream,
  pushPCM,
  endStream,
  interrupt,
  setState,
  setVisualization,
};

async function bootAvatar() {
  showStatus("DEMO AVATAR LOADING");
  try {
    head = new TalkingHead(container, {
      ttsEndpoint: "",
      lipsyncModules: ["en"],
      lipsyncLang: "en",
      cameraView: "head",
      cameraRotateEnable: false,
      cameraPanEnable: false,
      cameraZoomEnable: false,
      modelPixelRatio: 1,
      lightAmbientColor: 0x42dfff,
      lightAmbientIntensity: 2.2,
      lightDirectColor: 0x76eaff,
      lightDirectIntensity: 8,
      lightSpotColor: 0x00e5ff,
      lightSpotIntensity: 8,
      lightSpotPhi: 0.2,
      lightSpotTheta: 3.3,
      lightSpotDispersion: 0.9,
    });

    await head.showAvatar({
      url: "./assets/prototype-mpfb.glb",
      body: "F",
      avatarMood: "neutral",
      lipsyncLang: "en",
      avatarIdleEyeContact: 0.72,
      avatarIdleHeadMove: 0.38,
      avatarSpeakingEyeContact: 0.82,
      avatarSpeakingHeadMove: 0.42,
      baseline: { eyeBlinkLeft: 0.08, eyeBlinkRight: 0.08 },
    }, (event) => {
      if (event.lengthComputable) {
        showStatus(`DEMO AVATAR ${Math.min(100, Math.round(event.loaded / event.total * 100))}%`);
      }
    }, (gltf) => {
      gltf.scene.traverse((object) => {
        if (!object.isMesh) return;
        const name = object.name || "";
        if (/casualsuit|ponytail/i.test(name)) {
          object.visible = false;
          return;
        }
        const wasArray = Array.isArray(object.material);
        const materials = wasArray ? object.material : [object.material];
        const mapped = materials.map((source) => {
          const material = source.clone();
          const isEye = /high-poly/i.test(name);
          const isMouth = /teeth|tongue/i.test(name);
          const isFeature = /eyebrow|eyelash/i.test(name);
          // Remove realistic skin and hair textures while preserving the rig.
          for (const slot of ["map", "normalMap", "roughnessMap", "metalnessMap", "aoMap"]) {
            if (!isEye && slot in material) material[slot] = null;
          }
          if (material.color) material.color.setHex(isEye ? 0x4fa9b8 : 0x22cfe8);
          if (material.emissive) {
            material.emissive.setHex(isEye ? 0x073c48 : 0x063e53);
            material.emissiveIntensity = isEye ? 0.3 : (isFeature ? 1.4 : 1.0);
          }
          if ("metalness" in material) material.metalness = 0.08;
          if ("roughness" in material) material.roughness = isEye ? 0.16 : 0.54;
          material.transparent = true;
          material.opacity = isEye ? 0.98 : (isMouth ? 0.52 : (isFeature ? 0.72 : 0.62));
          material.depthWrite = isEye;
          material.side = THREE.FrontSide;
          material.onBeforeCompile = (shader) => {
            shader.uniforms.jarvisTime = { value: 0 };
            shader.uniforms.jarvisState = { value: hologramState };
            hologramShaders.push(shader);
            shader.fragmentShader = shader.fragmentShader.replace(
              "#include <common>",
              "#include <common>\nuniform float jarvisTime;\nuniform float jarvisState;"
            );
            shader.fragmentShader = shader.fragmentShader.replace(
              "#include <dithering_fragment>",
              `float jarvisFresnel = pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), 2.0);\n` +
              `vec2 jarvisCell = fract(gl_FragCoord.xy / 4.25) - 0.5;\n` +
              `float jarvisDot = 1.0 - smoothstep(0.12, 0.34, length(jarvisCell));\n` +
              `vec2 jarvisGrid = floor(gl_FragCoord.xy / 4.25);\n` +
              `float jarvisNoise = fract(sin(dot(jarvisGrid, vec2(12.9898, 78.233))) * 43758.5453);\n` +
              `jarvisDot *= step(0.16, jarvisNoise);\n` +
              `float jarvisScan = 0.55 + 0.45 * sin(gl_FragCoord.y * 0.32 - jarvisTime * 3.2);\n` +
              `float jarvisPulse = 0.88 + 0.12 * sin(jarvisTime * (1.4 + jarvisState * 0.35));\n` +
              (isEye
                ? `gl_FragColor.rgb *= vec3(0.32, 0.78, 0.88);\n` +
                  `gl_FragColor.rgb += vec3(0.01, 0.34, 0.46) * jarvisPulse * 0.08;\n` +
                  `gl_FragColor.a = min(1.0, gl_FragColor.a);\n`
                : `gl_FragColor.rgb = vec3(0.02, 0.68, 0.92) * (0.58 + jarvisDot * 0.76 + jarvisFresnel * 1.25) * jarvisPulse;\n` +
                  `gl_FragColor.a *= clamp(0.10 + jarvisDot * 0.58 + jarvisFresnel * 0.72 + jarvisScan * 0.10, 0.08, 0.88);\n`) +
              "#include <dithering_fragment>"
            );
          };
          material.customProgramCacheKey = () => `jarvis-hologram-v2-${isEye ? "eye" : "surface"}`;
          material.needsUpdate = true;
          return material;
        });
        object.material = wasArray ? mapped : mapped[0];
      });
    });

    mountSyntheticPortrait();

    const tickHologram = (time) => {
      for (const shader of hologramShaders) shader.uniforms.jarvisTime.value = time / 1000;
      requestAnimationFrame(tickHologram);
    };
    requestAnimationFrame(tickHologram);
    head.setView("head", { cameraDistance: -0.12, cameraY: 0.01 });
    ready = true;
    resolveReady();
    reactor.classList.add("avatar-ready");
    showStatus("SYNTHETIC PRESENCE · ORIGINAL PORTRAIT", "ready");
    setState(reactor.dataset.avatarState || "standby");
  } catch (error) {
    console.error("Demo avatar failed to load", error);
    reactor.classList.add("avatar-error");
    showStatus("AVATAR OFFLINE", "error");
  }
}

bootAvatar();
