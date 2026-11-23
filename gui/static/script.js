/* EchoOS GUI client: safe command submission, voice control and feedback. */
"use strict";

const orbRing = document.getElementById("orbRing");
const statusLabel = document.getElementById("statusLabel");
const responseCard = document.getElementById("responseCard");
const responseText = document.getElementById("responseText");
const cmdInput = document.getElementById("cmdInput");
const sendBtn = document.getElementById("sendBtn");
const modeBadge = document.getElementById("modeBadge");
const audioBadge = document.getElementById("audioBadge");
const robotWrap = document.getElementById("robotWrap");
const hfToggle = document.getElementById("hfToggle");

let currentState = "idle";
let sessionId = "user_" + Math.random().toString(36).slice(2, 9);
let pendingConfirmation = false;
let audioAvailable = false;
let commandInFlight = false;
let listenInFlight = null;
let handsFree = false;
let loopRunning = false;
let resumeHandsFreeAfterConfirmation = false;
let activeSpeechFinish = null;

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
    label: "EchoOS speaking…",
    color: "var(--accent2)"
  },
  confirming: {
    orb: "processing",
    label: "Confirmation required — say or type Yes / No",
    color: "var(--warn)"
  }
};

function setState(name) {
  currentState = name;
  const state = STATES[name] || STATES.idle;
  orbRing.className = "orb-ring" + (state.orb ? ` ${state.orb}` : "");
  statusLabel.textContent = state.label;
  statusLabel.style.color = state.color;
  robotWrap.classList.toggle("talking", name === "speaking");
}

function scheduleBlink() {
  const delayMs = 2500 + Math.random() * 4000;
  window.setTimeout(() => {
    const svg = document.querySelector(".robot-svg");
    if (svg) {
      svg.classList.add("blink");
      window.setTimeout(() => svg.classList.remove("blink"), 180);
    }
    scheduleBlink();
  }, delayMs);
}
scheduleBlink();

function speakText(text) {
  if (!("speechSynthesis" in window) ||
      typeof SpeechSynthesisUtterance === "undefined") {
    return Promise.resolve();
  }

  const cleanText = String(text || "")
    .replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, "")
    .trim();
  if (!cleanText) return Promise.resolve();

  if (activeSpeechFinish) activeSpeechFinish(true);

  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(cleanText);
    const isArabic = /[\u0600-\u06FF]/.test(cleanText);
    utterance.lang = isArabic ? "ar-SA" : "en-US";
    utterance.rate = 1.0;
    utterance.pitch = 1.05;

    let settled = false;
    let timeoutId = null;

    function finish(cancelSpeech = false) {
      if (settled) return;
      settled = true;
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      if (activeSpeechFinish === finish) activeSpeechFinish = null;
      if (cancelSpeech) window.speechSynthesis.cancel();
      resolve();
    }

    activeSpeechFinish = finish;
    utterance.onend = () => finish(false);
    utterance.onerror = () => finish(false);

    const timeoutMs = Math.max(15000, Math.min(60000, cleanText.length * 140 + 5000));
    timeoutId = window.setTimeout(() => finish(true), timeoutMs);

    try {
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      finish(true);
    }
  });
}

async function requestJSON(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error("Cannot reach the EchoOS server. Check that it is running.");
  }

  const body = await response.text();
  let data;
  try {
    data = body ? JSON.parse(body) : {};
  } catch (error) {
    throw new Error(`The server returned an invalid response (HTTP ${response.status}).`);
  }
  if (!response.ok) {
    throw new Error(data.message || `Request failed (HTTP ${response.status}).`);
  }
  return data;
}

function requestListen(mode) {
  const request = requestJSON("/api/listen", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ mode })
  });
  let tracked;
  tracked = request.finally(() => {
    if (listenInFlight === tracked) listenInFlight = null;
  });
  listenInFlight = tracked;
  return tracked;
}

async function fetchStatus() {
  try {
    const data = await requestJSON("/status");
    modeBadge.textContent = data.echoos_available ? "Core: online" : "Core: unavailable";
    modeBadge.className = data.echoos_available
      ? "mode-badge connected"
      : "mode-badge offline";

    audioAvailable = Boolean(data.audio_available);
    audioBadge.textContent = audioAvailable ? "Audio: ready" : "Audio: unavailable";
    audioBadge.className = audioAvailable
      ? "audio-badge ready"
      : "audio-badge unavailable";
    hfToggle.disabled = !audioAvailable;
    orbRing.classList.toggle("disabled", !audioAvailable);
    orbRing.setAttribute("aria-disabled", String(!audioAvailable));

    if (!audioAvailable && handsFree) setHandsFree(false, false);

    if (typeof data.pending_confirmation === "boolean") {
      pendingConfirmation = data.pending_confirmation;
      if (!pendingConfirmation && currentState === "confirming") {
        setState("idle");
        cmdInput.placeholder = "Type a command (e.g., system info, what time is it)…";
      }
    }
    return data;
  } catch (error) {
    modeBadge.textContent = "Core: offline";
    modeBadge.className = "mode-badge offline";
    audioAvailable = false;
    audioBadge.textContent = "Audio: unavailable";
    audioBadge.className = "audio-badge unavailable";
    hfToggle.disabled = true;
    orbRing.classList.add("disabled");
    orbRing.setAttribute("aria-disabled", "true");
    if (handsFree) setHandsFree(false, false);
    return null;
  }
}
fetchStatus();

function showResponse(text, status) {
  const isError = status === "error";
  const isWarning = ["needs_confirmation", "needs_clarification", "unknown"].includes(status);
  responseText.style.color = isError
    ? "var(--error)"
    : (isWarning ? "var(--warn)" : "var(--text)");
  responseText.textContent = text;
  responseCard.classList.add("visible");
}

function hideResponse() {
  responseCard.classList.remove("visible");
}

function showCommandResult(data) {
  const message = data.message || "Executed.";
  const displayText = data.heard_text
    ? `Heard: “${data.heard_text}”\n${message}`
    : message;
  showResponse(displayText, data.status || "ok");
}

async function sendCommand() {
  if (commandInFlight || sendBtn.disabled) return;
  const text = cmdInput.value.trim();
  if (!text) return;

  commandInFlight = true;
  sendBtn.disabled = true;

  const wasHandsFree = handsFree;
  if (wasHandsFree) {
    resumeHandsFreeAfterConfirmation = true;
    setHandsFree(false, false);
  }

  cmdInput.value = "";
  hideResponse();
  setState("processing");

  try {
    const data = await requestJSON("/command", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ text, session_id: sessionId })
    });

    const message = data.message || "Executed.";
    const status = data.status || "ok";
    showResponse(message, status);

    if (status === "needs_confirmation") {
      pendingConfirmation = true;
      setState("confirming");
      cmdInput.placeholder = "Type 'yes' to confirm or 'no' to cancel…";
      await speakText(message);
    } else {
      pendingConfirmation = false;
      const resume = resumeHandsFreeAfterConfirmation || wasHandsFree;
      resumeHandsFreeAfterConfirmation = false;
      cmdInput.placeholder = "Type a command (e.g., system info, what time is it)…";
      setState("speaking");
      await speakText(message);
      setState("idle");
      if (resume && audioAvailable) setHandsFree(true, false);
    }
  } catch (error) {
    showResponse(error.message || "Command request failed.", "error");
    setState("idle");
    const resume = resumeHandsFreeAfterConfirmation || wasHandsFree;
    resumeHandsFreeAfterConfirmation = false;
    if (resume && audioAvailable) setHandsFree(true, false);
  } finally {
    commandInFlight = false;
    sendBtn.disabled = false;
    cmdInput.focus();
  }
}

cmdInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    if (!commandInFlight && !sendBtn.disabled) sendCommand();
  }
});

orbRing.addEventListener("click", async () => {
  if (handsFree || !audioAvailable || listenInFlight) return;
  if (currentState !== "idle" && currentState !== "confirming") return;

  setState("listening");
  hideResponse();

  try {
    const data = await requestListen("once");
    if (data.status === "listen_cancelled" ||
        data.status === "confirmation_resolved") {
      setState(pendingConfirmation ? "confirming" : "idle");
      return;
    }
    if (data.status === "confirmation_waiting") {
      pendingConfirmation = true;
      setState("confirming");
      showResponse("Still waiting for confirmation. Say or type Yes / No.", "needs_confirmation");
      return;
    }

    showCommandResult(data);
    const status = data.status || "ok";
    if (status === "needs_confirmation") {
      pendingConfirmation = true;
      setState("confirming");
      cmdInput.placeholder = "Type 'yes' or 'no', or use the microphone to answer…";
      await speakText(data.message || "Please confirm.");
    } else {
      pendingConfirmation = false;
      const resume = resumeHandsFreeAfterConfirmation;
      resumeHandsFreeAfterConfirmation = false;
      setState("speaking");
      await speakText(data.message || "Done.");
      setState("idle");
      if (resume && audioAvailable) setHandsFree(true, false);
    }
  } catch (error) {
    setState(pendingConfirmation ? "confirming" : "idle");
    showResponse(error.message || "Microphone request failed.", "error");
  }
});

function setHandsFree(on, persist = true) {
  if (on && !audioAvailable) {
    showResponse("Native microphone audio is unavailable.", "error");
    on = false;
  }

  handsFree = Boolean(on);
  hfToggle.classList.toggle("on", handsFree);
  hfToggle.textContent = handsFree ? "Hands-free: on" : "Hands-free: off";
  hfToggle.disabled = !audioAvailable;

  if (persist) {
    try {
      localStorage.setItem("echoos_hf", handsFree ? "1" : "0");
    } catch (error) {
      // Browser storage may be disabled.
    }
  }

  if (handsFree) {
    handsFreeLoop();
  } else if (currentState === "listening") {
    setState(pendingConfirmation ? "confirming" : "idle");
  }
}

async function handsFreeLoop() {
  if (loopRunning || !audioAvailable) return;
  loopRunning = true;
  let mode = "standby";
  let errors = 0;

  try {
    while (handsFree) {
      if (commandInFlight || currentState === "processing" || currentState === "speaking") {
        await delay(250);
        continue;
      }

      setState(mode === "session" || pendingConfirmation ? "listening" : "idle");

      let data;
      try {
        data = await requestListen(mode);
      } catch (error) {
        if (!handsFree) break;
        errors += 1;
        showResponse(error.message || "Microphone request failed.", "error");
        await delay(Math.min(5000, 1000 * errors));
        continue;
      }

      if (!handsFree) break;
      const status = data.status || "ok";

      if (status === "listen_cancelled") continue;
      if (status === "confirmation_resolved") {
        pendingConfirmation = false;
        mode = "standby";
        continue;
      }
      if (status === "confirmation_waiting") {
        pendingConfirmation = true;
        setState("confirming");
        await delay(250);
        continue;
      }
      if (status === "standby_idle") {
        if (data.heard_text) {
          showResponse(`Heard: “${data.heard_text}” — say “Hi Echo” first`, "unknown");
        }
        continue;
      }
      if (status === "session_end") {
        mode = "standby";
        pendingConfirmation = false;
        continue;
      }
      if (status === "error" || status === "no_speech") {
        errors += 1;
        showResponse(data.message || "Microphone error.", "error");
        await delay(Math.min(5000, 1000 * errors));
        continue;
      }

      errors = 0;
      mode = "session";
      showCommandResult(data);

      if (status === "needs_confirmation") {
        pendingConfirmation = true;
        setState("confirming");
        cmdInput.placeholder = "Say or type 'yes' to confirm, or 'no' to cancel…";
        await speakText(data.message || "Please confirm.");
      } else {
        pendingConfirmation = false;
        cmdInput.placeholder = "Type a command (e.g., system info, what time is it)…";
        setState("speaking");
        await speakText(data.message || "Done.");
        setState("idle");
      }
    }
  } finally {
    loopRunning = false;
  }
}

hfToggle.addEventListener("click", () => setHandsFree(!handsFree));

function delay(ms) {
  return new Promise(resolve => window.setTimeout(resolve, ms));
}

window.addEventListener("load", async () => {
  cmdInput.focus();
  let savedHandsFree = null;
  try {
    savedHandsFree = localStorage.getItem("echoos_hf");
  } catch (error) {
    // Ignore unavailable localStorage.
  }

  const data = await fetchStatus();
  if (data && data.audio_available && savedHandsFree !== "0") {
    setHandsFree(true, false);
  }
  window.setInterval(fetchStatus, 10000);
});
