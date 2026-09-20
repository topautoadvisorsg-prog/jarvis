import { TalkingHead } from "talkinghead";

const container = document.getElementById("avatarStage");
const reactor = document.getElementById("reactorWrap");
const status = document.getElementById("avatarStatus");

let head = null;
let ready = false;
let mouthTimer = null;
let mouthLevel = 0;
const scheduledMouth = new Set();

function showStatus(text, kind = "") {
  status.textContent = text;
  status.dataset.kind = kind;
}

function resetMouth(fast = false) {
  mouthLevel = 0;
  if (!head) return;
  for (const key of ["jawOpen", "mouthOpen", "mouthPucker", "mouthFunnel"]) {
    try { head.setFixedValue(key, null, fast ? 25 : 100); } catch {}
  }
}

function audioEnergy(buffer) {
  const samples = new Int16Array(buffer);
  if (!samples.length) return 0;
  let sum = 0;
  let crossings = 0;
  let previous = samples[0];
  for (let i = 0; i < samples.length; i += 3) {
    const value = samples[i];
    const normalized = value / 32768;
    sum += normalized * normalized;
    if ((value >= 0) !== (previous >= 0)) crossings++;
    previous = value;
  }
  const count = Math.ceil(samples.length / 3);
  return {
    rms: Math.sqrt(sum / Math.max(1, count)),
    brightness: Math.min(1, crossings / Math.max(1, count) * 8),
  };
}

function ingestPCM(buffer) {
  if (!ready || !head || reactor.classList.contains("avatar-visualizing")) return;
  const { rms, brightness } = audioEnergy(buffer);
  const target = Math.max(0, Math.min(1, (rms - 0.012) * 7.5));
  mouthLevel = mouthLevel * 0.35 + target * 0.65;
  try {
    head.setFixedValue("jawOpen", mouthLevel, 28);
    head.setFixedValue("mouthOpen", mouthLevel * 0.82, 28);
    head.setFixedValue("mouthPucker", brightness * mouthLevel * 0.22, 35);
    head.setFixedValue("mouthFunnel", (1 - brightness) * mouthLevel * 0.16, 35);
  } catch {}
  clearTimeout(mouthTimer);
  mouthTimer = setTimeout(() => resetMouth(), 130);
}

function setState(next) {
  reactor.dataset.avatarState = next || "standby";
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

function interrupt() {
  for (const timer of scheduledMouth) clearTimeout(timer);
  scheduledMouth.clear();
  clearTimeout(mouthTimer);
  mouthLevel = 0;
  if (head) {
    for (const key of ["jawOpen", "mouthOpen", "mouthPucker", "mouthFunnel"]) {
      try { head.setFixedValue(key, 0, 18); } catch {}
    }
    mouthTimer = setTimeout(() => resetMouth(true), 240);
  }
  try { head?.streamInterrupt?.(); } catch {}
}

function schedulePCM(buffer, delayMs = 0, durationMs = 120) {
  if (!ready) return;
  const startTimer = setTimeout(() => {
    scheduledMouth.delete(startTimer);
    ingestPCM(buffer);
    clearTimeout(mouthTimer);
    mouthTimer = setTimeout(() => resetMouth(), Math.max(70, durationMs + 25));
  }, Math.max(0, delayMs));
  scheduledMouth.add(startTimer);
}

function setVisualization(active) {
  reactor.classList.toggle("avatar-visualizing", Boolean(active));
}

window.JarvisAvatar = {
  get ready() { return ready; },
  schedulePCM,
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
      lightAmbientIntensity: 1.8,
      lightDirectColor: 0x76eaff,
      lightDirectIntensity: 18,
      lightSpotColor: 0x00e5ff,
      lightSpotIntensity: 12,
      lightSpotPhi: 0.2,
      lightSpotTheta: 3.3,
      lightSpotDispersion: 0.9,
    });

    await head.showAvatar({
      url: "./assets/prototype-brunette.glb",
      body: "F",
      avatarMood: "neutral",
      lipsyncLang: "en",
      avatarIdleEyeContact: 0.72,
      avatarIdleHeadMove: 0.38,
      avatarSpeakingEyeContact: 0.82,
      avatarSpeakingHeadMove: 0.42,
      baseline: { eyeBlinkLeft: 0.04, eyeBlinkRight: 0.04 },
    }, (event) => {
      if (event.lengthComputable) {
        showStatus(`DEMO AVATAR ${Math.min(100, Math.round(event.loaded / event.total * 100))}%`);
      }
    }, (gltf) => {
      gltf.scene.traverse((object) => {
        if (!object.isMesh) return;
        const wasArray = Array.isArray(object.material);
        const materials = wasArray ? object.material : [object.material];
        const mapped = materials.map((source) => {
          const material = source.clone();
          if (material.color) material.color.multiplyScalar(0.72).lerp({ r: 0.08, g: 0.82, b: 1 }, 0.34);
          if (material.emissive) {
            material.emissive.setHex(0x052f46);
            material.emissiveIntensity = 0.65;
          }
          material.transparent = true;
          material.opacity = 0.88;
          material.depthWrite = true;
          return material;
        });
        object.material = wasArray ? mapped : mapped[0];
      });
    });

    head.setView("head", { cameraDistance: 0.05, cameraY: 0.01 });
    ready = true;
    reactor.classList.add("avatar-ready");
    showStatus("PROTOTYPE FACE · INTERNAL ONLY", "ready");
    setState(reactor.dataset.avatarState || "standby");
  } catch (error) {
    console.error("Demo avatar failed to load", error);
    reactor.classList.add("avatar-error");
    showStatus("AVATAR OFFLINE", "error");
  }
}

bootAvatar();
