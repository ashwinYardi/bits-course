/**
 * Generate name-agnostic neural voiceover MP3s for all Bits University
 * characters and Karpathy comms using open-weight Kokoro-82M (₹0 / $0).
 *
 * Usage:
 *   NODE_USE_ENV_PROXY=1 NODE_PATH=/tmp/ttsgen/node_modules node scripts/generate_voices.mjs
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";

const TTS_PKG_DIR = process.env.TTS_NODE_MODULES || "/tmp/ttsgen/node_modules";
const kokoroPkg = JSON.parse(fs.readFileSync(path.join(TTS_PKG_DIR, "kokoro-js/package.json"), "utf8"));
const kokoroEntry = kokoroPkg.exports?.["."]?.import || kokoroPkg.main || "dist/kokoro.js";
const { KokoroTTS } = await import(pathToFileURL(path.join(TTS_PKG_DIR, "kokoro-js", kokoroEntry)).href);

const lamePkg = JSON.parse(fs.readFileSync(path.join(TTS_PKG_DIR, "@breezystack/lamejs/package.json"), "utf8"));
const lameEntry = lamePkg.exports?.["."]?.import || lamePkg.module || lamePkg.main;
const lameModule = await import(pathToFileURL(path.join(TTS_PKG_DIR, "@breezystack/lamejs", lameEntry)).href);
const Mp3Encoder = lameModule.Mp3Encoder || lameModule.default?.Mp3Encoder;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(__dirname, "..", "audio");
fs.mkdirSync(OUT_DIR, { recursive: true });

// Distinct high-grade Kokoro-82M voice casting
const CAST = {
  karpathy: { voice: "am_michael", speed: 1.06, label: "Andrej Karpathy" },
  rajan:    { voice: "am_fenrir",  speed: 1.02, label: "Officer Rajan" },
  maya:     { voice: "af_bella",   speed: 1.04, label: "Maya" },
  kabir:    { voice: "bm_george",  speed: 1.00, label: "Chef Kabir" },
  meera:    { voice: "bf_emma",    speed: 1.00, label: "Prof. Meera" },
};

// All 19 name-agnostic spoken scripts (natural pronunciation for math, symbols & acronyms)
const CLIPS = [
  // --- Andrej Karpathy (Intro + 6 Pocket Communicator calls) ---
  {
    id: "karpathy_intro",
    actor: "karpathy",
    text: "Yo — sorry to hijack your speakers! Look: we built Bits University for one reason. Passive threads and shallow tutorials don't make AI experts — touching the real logits, B P E merges, vector angles, and K V caches yourself does. Finish every checkpoint, steal the copyable Agent Prompts inside each lab to push even further, and remember rule number one of this campus: having fun is non-negotiable. Now walk up the South Road — Officer Rajan is waiting at the boom gate!",
  },
  {
    id: "karpathy_arrival",
    actor: "karpathy",
    text: "Yo! I dropped you the secret pin to our self-expanding AI campus. Walk up the South Road and head inside!",
  },
  {
    id: "karpathy_after_l0-what-is-an-llm",
    actor: "karpathy",
    text: "Haha, I knew Officer Rajan would ambush you at the boom barrier! Now you know the secret: an L L M is just a one-word relay runner rolling a temperature-weighted die. Head west to Maya's Parking Lot — she'll show you why AI can't count the R's in strawberry!",
  },
  {
    id: "karpathy_after_l0-tokens",
    actor: "karpathy",
    text: "Three point six times more tokens for Hindi than English — wild, right? Every frontier lab is fighting tokenizer efficiency right now. Next stop: grab a cup of chai with Chef Kabir on the Terrace and see how raw barcode IDs turn into four-D Meaning G P S!",
  },
  {
    id: "karpathy_after_l0-embeddings",
    actor: "karpathy",
    text: "King minus man plus woman equals queen! Once words become coordinates in meaning space, you can search all of human knowledge by flashlight angle. Walk over to Professor Meera at the Central Quad Fountain — she's running the Amnesia Chef lunch tray experiment!",
  },
  {
    id: "karpathy_after_l0-context-window",
    actor: "karpathy",
    text: "You survived the twenty-four-word Lunch Tray and the Lost-in-the-Middle U-curve! The cranes on the East Lawn just finished all six Academic Halls — fifty-three modules, updated for Multimodal, Context Engineering, R L V R, G R P O, and Training Stability! Step inside Hall Zero whenever you're ready!",
  },
  {
    id: "karpathy_manual",
    actor: "karpathy",
    text: "Hey! Remember: every time a new paper or model architecture drops, our campus cranes construct a new room automatically. Never memorize jargon — test the toy mechanism in pure Python first!",
  },

  // --- Officer Rajan (Stop 01: South Gate) ---
  {
    id: "npc_l0-what-is-an-llm_0",
    actor: "rajan",
    text: "Peep! Whoa there! Did Karpathy call you and tell you that you could just stroll right through my South Gate? Not on my watch! Last week I turned away three AI VPs who thought ChatGPT has a tiny philosopher inside. Tell me: what is an L L M actually doing when it replies?",
  },
  {
    id: "npc_l0-what-is-an-llm_1",
    actor: "rajan",
    text: "Ha! Respect for honesty! An L L M has no master plan and no backspace key. It scores every word in the dictionary, rolls a weighted die controlled by Temperature and Top-P, glues that one winning word onto your prompt, and repeats until the end-of-sequence token! Test my Guard Booth Simulator or pass the three-question check to lift this barrier!",
  },
  {
    id: "npc_l0-what-is-an-llm_cleared",
    actor: "rajan",
    text: "Welcome back through the South Gate! You already passed my Security Boom Check — the barrier stays wide open for you. Want to revise Chapter One, re-run the Python lab, or head straight to your next campus mission?",
  },

  // --- Maya (Stop 02: Parking Lot) ---
  {
    id: "npc_l0-tokens_0",
    actor: "maya",
    text: "Hey! You got Officer Rajan to lift the boom gate! Look at these three parked cars in my lot: S T R number four ninety six, A W number six seventy five, and berry number fifteen thousand seven hundred seventeen. Ever wondered why a billion-dollar AI embarrassed itself counting the letter R in strawberry?",
  },
  {
    id: "npc_l0-tokens_1",
    actor: "maya",
    text: "Because an AI never reads letters! My B P E Token Chopper runs regex pre-tokenization and glues common chunks into integer barcodes before the AI even wakes up. Two of the R's are sealed inside barcode fifteen thousand seven hundred seventeen, berry! Come try the live Barcode Chopper inside Chapter Two.",
  },
  {
    id: "npc_l0-tokens_cleared",
    actor: "maya",
    text: "Hey! Your Parking Lot Barcode pass is already stamped. Swing by anytime you want to test custom words in my live B P E Chopper, review regex pre-tokenization and the three point six times Hindi tax, or walk over to your next stop!",
  },

  // --- Chef Kabir (Stop 03: Chai Terrace) ---
  {
    id: "npc_l0-embeddings_0",
    actor: "kabir",
    text: "Pull up a chair under the umbrella! In Maya's dictionary, barcode forty thousand, coffee, sits right next to forty thousand and one, coffin. Why doesn't the AI accidentally serve you a coffin when you order filter coffee?",
  },
  {
    id: "npc_l0-embeddings_1",
    actor: "kabir",
    text: "Spot on! The moment a barcode enters the model, we trade it for an Embedding — a list of G P S coordinates on a giant Meaning Map. Here on my patio, masala chai and filter coffee sit just nine point seven degrees apart, at zero point nine eight five eight similarity, while Kubernetes sits eighty-eight point two degrees away! Come explore the Vector Angle Compass.",
  },
  {
    id: "npc_l0-embeddings_cleared",
    actor: "kabir",
    text: "Fresh cutting chai on the house! You already cleared the Cafeteria Meaning Map. Want to spin the two-D Vector Angle Compass, revisit the Antonym Trap and Hybrid Search, or head to your next mission?",
  },

  // --- Prof. Meera (Stop 04: Central Quad Fountain) ---
  {
    id: "npc_l0-context-window_0",
    actor: "meera",
    text: "Listen to the fountain. People think when they chat with an AI for an hour, the AI is getting to know them. False! The AI is an Amnesia Chef whose brain resets to zero after every single reply. All it ever sees is what fits on a fixed-size lunch tray right now!",
  },
  {
    id: "npc_l0-context-window_1",
    actor: "meera",
    text: "When the tray hits its twenty-four-word limit, the oldest words at the left edge literally slide off into the trash — taking your Turn One locker code seven four nine two with them! Worse, even when everything fits, attention follows a U-curve: ninety-three percent recall at the edges versus thirty-eight point seven percent in the middle, while K V Prefix Caching saves eighty-one percent on repeated turns!",
  },
  {
    id: "npc_l0-context-window_cleared",
    actor: "meera",
    text: "Great to see you back by the Quad Fountain! You've mastered Context Windows and K V Prefix Caching. Want to revise Chapter Four, inspect the O of N squared lab output, or walk into the Academic Halls?",
  },
];

function floatToMp3(floatSamples, sampleRate, kbps = 64) {
  const pcm = new Int16Array(floatSamples.length);
  for (let i = 0; i < floatSamples.length; i++) {
    const s = Math.max(-1, Math.min(1, floatSamples[i]));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  const encoder = new Mp3Encoder(1, sampleRate, kbps);
  const chunks = [];
  const blockSize = 1152;
  for (let i = 0; i < pcm.length; i += blockSize) {
    const buf = encoder.encodeBuffer(pcm.subarray(i, i + blockSize));
    if (buf.length > 0) chunks.push(Buffer.from(buf));
  }
  const tail = encoder.flush();
  if (tail.length > 0) chunks.push(Buffer.from(tail));
  return Buffer.concat(chunks);
}

console.log("Loading Kokoro-82M (q8)...");
const tts = await KokoroTTS.from_pretrained("onnx-community/Kokoro-82M-v1.0-ONNX", { dtype: "q8" });

const manifest = {};
let totalBytes = 0;
let totalSecs = 0;

for (let idx = 0; idx < CLIPS.length; idx++) {
  const clip = CLIPS[idx];
  const actor = CAST[clip.actor];
  const t0 = Date.now();
  const out = await tts.generate(clip.text, { voice: actor.voice, speed: actor.speed });
  const durationSec = +(out.audio.length / out.sampling_rate).toFixed(2);
  const mp3 = floatToMp3(out.audio, out.sampling_rate, 64);
  const filePath = path.join(OUT_DIR, `${clip.id}.mp3`);
  fs.writeFileSync(filePath, mp3);
  totalBytes += mp3.length;
  totalSecs += durationSec;
  manifest[clip.id] = {
    file: `audio/${clip.id}.mp3`,
    actor: actor.label,
    voice: actor.voice,
    durationSec,
    bytes: mp3.length,
  };
  console.log(
    `[${String(idx + 1).padStart(2, "0")}/${CLIPS.length}] ${clip.id}.mp3 (${actor.voice}) -> ${durationSec}s, ${(mp3.length / 1024).toFixed(1)} KB (${Date.now() - t0}ms)`
  );
}

fs.writeFileSync(path.join(OUT_DIR, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`\nDONE! Generated ${CLIPS.length} MP3s: ${totalSecs.toFixed(1)}s total, ${(totalBytes / 1024 / 1024).toFixed(2)} MB.`);
