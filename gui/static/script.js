/* ══════════════════════════════════════════════════════
   EchoOS GUI — Client Script (Step 2 Standalone & Core)
   Features:
   - Spoken feedback (TTS via Web Speech Synthesis)
   - Two-way Confirmation Lifecycle (needs_confirmation)
   - Visual robot animation matching actual speech length
   - Session tracking
   ══════════════════════════════════════════════════════ */

"use strict";

// ── DOM Elements ─────────────────────────────────────────
const orbRing      = document.getElementById("orbRing");
const statusLabel  = document.getElementById("statusLabel");
const responseCard = document.getElementById("responseCard");
const responseText = document.getElementById("responseText");
const cmdInput     = document.getElementById("cmdInput");
const sendBtn      = document.getElementById("sendBtn");
const modeBadge    = document.getElementById("modeBadge");
const robotWrap    = document.getElementById("robotWrap");
const hfToggle     = document.getElementById("hfToggle");

// ── State ────────────────────────────────────────────────
let currentState = "idle";
let sessionId    = "user_" + Math.random().toString(36).substring(2, 9);
let pendingConfirmation = false;
let blinkTimer   = null;

// ── States Definition ────────────────────────────────────
const STATES = {
  idle: {
    orb: "",
    label: 'EchoOS ready — say "Hi Echo" or type an action',
    color: "var(--text-dim)"
  },
  listening: {
    orb: "listening",
    label: "Listening for your voice…",
    color: "var(--success)"
  },
  processing: {
    orb: "processing",
    label: "Processing command…",
    color: "var(--warn)"
  },
  speaking: {
    orb: "speaking",
    label: "EchoOS Speaking…",
    color: "var(--accent2)"
  },
  confirming: {
    orb: "processing",
    label: "Confirmation required (Say 'Yes' or 'No')",
    color: "var(--warn)"
  }
};

function setState(name) {
  currentState = name;
  const s = STATES[name] || STATES.idle;

  orbRing.className = "orb-ring" + (s.orb ? ` ${s.orb}` : "");
  statusLabel.textContent = s.label;
  statusLabel.style.color = s.color;

  if (name === "speaking") {
    robotWrap.classList.add("talking");
  } else {
    robotWrap.classList.remove("talking");
  }
}

// ── Robot Eye Blink ──────────────────────────────────────
function scheduleBlink() {
  const delay = 2500 + Math.random() * 4000;
  blinkTimer = setTimeout(() => {
    const svg = document.querySelector(".robot-svg");
    if (svg) {
      svg.classList.add("blink");
      setTimeout(() => svg.classList.remove("blink"), 180);
    }
    scheduleBlink();
  }, delay);
}
scheduleBlink();

// ── Spoken Feedback (TTS) ────────────────────────────────
function speakText(text) {
  if (!("speechSynthesis" in window)) return Promise.resolve();

  return new Promise((resolve) => {
    // Strip emojis for clean TTS pronunciation
    const cleanText = text.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, "").trim();
    if (!cleanText) {
      resolve();
      return;
    }

    window.speechSynthesis.cancel(); // Stop any pending speech
    const utterance = new SpeechSynthesisUtterance(cleanText);

    // Auto-detect Arabic vs English
    const isArabic = /[\u0600-\u06FF]/.test(cleanText);
    utterance.lang = isArabic ? "ar-SA" : "en-US";
    utterance.rate = 1.0;
    utterance.pitch = 1.05;

    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();

    // Failsafe timeout in case onend never triggers
    setTimeout(resolve, Math.min(10000, cleanText.length * 90 + 1500));

    window.speechSynthesis.speak(utterance);
  });
}

// ── Fetch Server Status ──────────────────────────────────
async function fetchStatus() {
  try {
    const r = await fetch("/status");
    const d = await r.json();
    if (d.echoos_available) {
      modeBadge.textContent = "EchoOS Core";
      modeBadge.className = "mode-badge connected";
    } else {
      modeBadge.textContent = `Mock — ${d.platform}`;
      modeBadge.className = "mode-badge mock";
    }
  } catch {
    modeBadge.textContent = "Offline";
    modeBadge.className = "mode-badge";
  }
}
fetchStatus();

// ── Response Display ─────────────────────────────────────
function showResponse(text, status) {
  const isErr = (status === "error");
  const isWarn = (status === "needs_confirmation" || status === "needs_clarification" || status === "unknown");

  if (isErr) responseText.style.color = "var(--error)";
  else if (isWarn) responseText.style.color = "var(--warn)";
  else responseText.style.color = "var(--text)";

  responseText.textContent = text;
  responseCard.classList.add("visible");
}

function hideResponse() {
  responseCard.classList.remove("visible");
}

// ── Send Command ─────────────────────────────────────────
async function sendCommand() {
  const text = cmdInput.value.trim();
  if (!text) return;

  cmdInput.value = "";
  sendBtn.disabled = true;
  hideResponse();

  setState("processing");

  try {
    const res = await fetch("/command", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ text, session_id: sessionId }),
    });

    const data = await res.json();
    const msg = data.message || "Executed.";
    const status = data.status || "ok";

    showResponse(msg, status);

    if (status === "needs_confirmation") {
      pendingConfirmation = true;
      setState("confirming");
      cmdInput.placeholder = "Type 'yes' to confirm or 'no' to cancel…";
      await speakText(msg);
    } else {
      pendingConfirmation = false;
      cmdInput.placeholder = "Type a command (e.g., system info, what time is it)…";
      setState("speaking");
      await speakText(msg);
      setState("idle");
    }

  } catch (err) {
    setState("speaking");
    showResponse("Connection error — is the server running?", "error");
    await delay(1500);
    setState("idle");
  }

  sendBtn.disabled = false;
  cmdInput.focus();
}

// ── Keyboard Enter ───────────────────────────────────────
cmdInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendCommand();
});

// ── Orb Click (Native PC Microphone via EchoOS audio.py + Whisper) ─────────
orbRing.addEventListener("click", async () => {
  if (handsFree) return; // hands-free is already listening
  if (currentState !== "idle" && currentState !== "confirming") return;

  setState("listening");
  hideResponse();

  try {
    const res = await fetch("/api/listen", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ mode: "once" }),
    });

    const data = await res.json();
    const msg = data.message || "Executed.";
    const status = data.status || "ok";

    // If text was recognized, display it in the input briefly
    if (data.heard_text) {
      cmdInput.value = data.heard_text;
    }

    showResponse(msg, status);

    if (status === "needs_confirmation") {
      pendingConfirmation = true;
      setState("confirming");
      cmdInput.placeholder = "Type 'yes' to confirm or 'no' to cancel…";
      await speakText(msg);
    } else {
      pendingConfirmation = false;
      cmdInput.placeholder = "Type a command (e.g., system info, what time is it)…";
      setState("speaking");
      await speakText(msg);
      setState("idle");
    }

  } catch (err) {
    setState("idle");
    showResponse("تعذر تشغيل الميكروفون أو حدث خطأ في الاتصال.", "error");
  }
});

// ── Hands-free: wait for "Hi Echo", then take commands ─────────────────────
// Same rules as the voice loop in main.py: standby until the wake word, then a
// session where commands need no wake word, and silence ends the session.
let handsFree = false;
let loopRunning = false;

function setHandsFree(on) {
  handsFree = on;
  hfToggle.classList.toggle("on", on);
  hfToggle.textContent = on ? "Hands-free: on" : "Hands-free: off";
  try { localStorage.setItem("echoos_hf", on ? "1" : "0"); } catch (e) {}
  if (on) handsFreeLoop();
  else if (currentState === "listening") setState("idle");
}

async function handsFreeLoop() {
  if (loopRunning) return;
  loopRunning = true;
  let mode = "standby";
  let errors = 0;

  while (handsFree) {
    // A typed command is running or being read aloud: wait for it.
    if (currentState === "processing" || currentState === "speaking") {
      await delay(300);
      continue;
    }

    setState(mode === "session" || pendingConfirmation ? "listening" : "idle");

    let data;
    try {
      const res = await fetch("/api/listen", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ mode }),
      });
      data = await res.json();
    } catch (err) {
      showResponse("Connection error — is the server running?", "error");
      await delay(2000);
      continue;
    }

    if (!handsFree) break;
    const status = data.status || "ok";

    if (status === "standby_idle") continue;

    if (status === "session_end") {
      mode = "standby";
      pendingConfirmation = false;
      continue;
    }

    if (status === "error" || status === "no_speech") {
      // Microphone problem or the mic is busy: show it, slow down, try again.
      errors += 1;
      showResponse(data.message || "Microphone error.", "error");
      await delay(Math.min(5000, 1000 * errors));
      continue;
    }

    errors = 0;
    mode = "session";
    if (data.heard_text) cmdInput.value = data.heard_text;

    const msg = data.message || "Executed.";
    showResponse(msg, status);

    if (status === "needs_confirmation") {
      pendingConfirmation = true;
      setState("confirming");
      cmdInput.placeholder = "Say or type 'yes' to confirm, or 'no' to cancel…";
    } else {
      pendingConfirmation = false;
      cmdInput.placeholder = "Type a command (e.g., system info, what time is it)…";
      setState("speaking");
    }

    // Don't listen while speaking, or the mic would hear EchoOS itself.
    await speakText(msg);
    if (status !== "needs_confirmation") setState("idle");
  }

  loopRunning = false;
}

hfToggle.addEventListener("click", () => setHandsFree(!handsFree));

// ── Helper ───────────────────────────────────────────────
function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

window.addEventListener("load", async () => {
  cmdInput.focus();

  // Start hands-free by default when the microphone is available.
  let saved = null;
  try { saved = localStorage.getItem("echoos_hf"); } catch (e) {}
  try {
    const st = await (await fetch("/status")).json();
    if (st.audio_available && saved !== "0") setHandsFree(true);
  } catch (e) {}
});
