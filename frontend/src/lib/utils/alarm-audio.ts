/**
 * Alarm sound synthesis using the Web Audio API.
 *
 * Generates distinct tones for each alarm sound type. No audio files needed.
 * Lazily creates a shared AudioContext on first use.
 */

export type SoundType = "beep" | "chime" | "buzz" | "siren";
export type RepeatMode = "once" | "3x";

let audioCtx: AudioContext | null = null;
let idCounter = 0;

const activeSounds = new Map<string, { stop: () => void }>();

function getAudioContext(): AudioContext | null {
  if (typeof globalThis.AudioContext === "undefined") return null;
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

function generatePlaybackId(): string {
  return `alarm-sound-${Date.now()}-${idCounter++}`;
}

// ──────────────────────────────────────────────
// Sound pattern definitions
// ──────────────────────────────────────────────

function playBeepPattern(ctx: AudioContext, onDone: () => void): () => void {
  let cancelled = false;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.value = 880;
  gain.gain.value = 0.4;
  osc.connect(gain);
  gain.connect(ctx.destination);

  const now = ctx.currentTime;
  // 200ms on, then off
  gain.gain.setValueAtTime(0.4, now);
  gain.gain.setValueAtTime(0, now + 0.2);
  osc.start(now);
  osc.stop(now + 0.4);
  osc.onended = () => {
    if (!cancelled) onDone();
  };

  return () => {
    cancelled = true;
    try {
      osc.stop();
    } catch {
      // already stopped
    }
    osc.disconnect();
    gain.disconnect();
  };
}

function playChimePattern(ctx: AudioContext, onDone: () => void): () => void {
  let cancelled = false;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "triangle";
  osc.frequency.value = 1047;
  gain.gain.value = 0.35;
  osc.connect(gain);
  gain.connect(ctx.destination);

  const now = ctx.currentTime;
  // Sweep from 1047 Hz to 523 Hz over 300ms
  osc.frequency.setValueAtTime(1047, now);
  osc.frequency.linearRampToValueAtTime(523, now + 0.3);
  gain.gain.setValueAtTime(0.35, now);
  gain.gain.linearRampToValueAtTime(0, now + 0.4);
  osc.start(now);
  osc.stop(now + 0.5);
  osc.onended = () => {
    if (!cancelled) onDone();
  };

  return () => {
    cancelled = true;
    try {
      osc.stop();
    } catch {
      // already stopped
    }
    osc.disconnect();
    gain.disconnect();
  };
}

function playBuzzPattern(ctx: AudioContext, onDone: () => void): () => void {
  let cancelled = false;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sawtooth";
  osc.frequency.value = 440;
  gain.gain.value = 0.25;
  osc.connect(gain);
  gain.connect(ctx.destination);

  const now = ctx.currentTime;
  // 150ms on, then off
  gain.gain.setValueAtTime(0.25, now);
  gain.gain.setValueAtTime(0, now + 0.15);
  osc.start(now);
  osc.stop(now + 0.35);
  osc.onended = () => {
    if (!cancelled) onDone();
  };

  return () => {
    cancelled = true;
    try {
      osc.stop();
    } catch {
      // already stopped
    }
    osc.disconnect();
    gain.disconnect();
  };
}

function playSirenPattern(ctx: AudioContext, onDone: () => void): () => void {
  let cancelled = false;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  gain.gain.value = 0.35;
  osc.connect(gain);
  gain.connect(ctx.destination);

  const now = ctx.currentTime;
  // Oscillate 660-880 Hz over 500ms cycle
  osc.frequency.setValueAtTime(660, now);
  osc.frequency.linearRampToValueAtTime(880, now + 0.25);
  osc.frequency.linearRampToValueAtTime(660, now + 0.5);
  gain.gain.setValueAtTime(0.35, now);
  gain.gain.linearRampToValueAtTime(0, now + 0.55);
  osc.start(now);
  osc.stop(now + 0.6);
  osc.onended = () => {
    if (!cancelled) onDone();
  };

  return () => {
    cancelled = true;
    try {
      osc.stop();
    } catch {
      // already stopped
    }
    osc.disconnect();
    gain.disconnect();
  };
}

const PATTERN_PLAYERS: Record<
  SoundType,
  (ctx: AudioContext, onDone: () => void) => () => void
> = {
  beep: playBeepPattern,
  chime: playChimePattern,
  buzz: playBuzzPattern,
  siren: playSirenPattern,
};

// ──────────────────────────────────────────────
// Public API
// ──────────────────────────────────────────────

/**
 * Play an alarm sound. Returns a playbackId for later stopping.
 * Returns empty string if AudioContext is unavailable.
 */
export function playAlarmSound(sound: SoundType, repeat: RepeatMode): string {
  const maybeCtx = getAudioContext();
  if (!maybeCtx) return "";

  const ctx: AudioContext = maybeCtx;
  const playbackId = generatePlaybackId();
  const maxPlays = repeat === "3x" ? 3 : 1;
  let playCount = 0;
  let currentStop: (() => void) | null = null;

  function playNext() {
    if (!activeSounds.has(playbackId)) return;
    playCount++;
    currentStop = PATTERN_PLAYERS[sound](ctx, () => {
      if (playCount < maxPlays && activeSounds.has(playbackId)) {
        playNext();
      } else {
        activeSounds.delete(playbackId);
      }
    });
  }

  activeSounds.set(playbackId, {
    stop: () => {
      currentStop?.();
      activeSounds.delete(playbackId);
    },
  });

  playNext();
  return playbackId;
}

/**
 * Stop a currently playing alarm sound.
 */
export function stopAlarmSound(playbackId: string): void {
  const entry = activeSounds.get(playbackId);
  if (entry) {
    entry.stop();
  }
}

/**
 * Stop all currently playing alarm sounds.
 */
export function stopAllAlarmSounds(): void {
  for (const entry of activeSounds.values()) {
    entry.stop();
  }
  activeSounds.clear();
}

/**
 * Check if a playback is currently active.
 */
export function isPlaying(playbackId: string): boolean {
  return activeSounds.has(playbackId);
}

/** Reset internal state (for testing only). */
export function _resetForTesting(): void {
  stopAllAlarmSounds();
  audioCtx = null;
}
