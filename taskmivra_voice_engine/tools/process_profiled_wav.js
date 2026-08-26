#!/usr/bin/env node
import fs from 'node:fs';
import { TaskMivraVoiceEngine } from '../src/voice_engine.js';
import { decodePcm16Wav, encodePcm16MonoWav } from '../src/wav.js';

const [profilePath, inputPath, outputPath, profileJsonPath] = process.argv.slice(2);
if (!profilePath || !inputPath || !outputPath) {
  console.error('Usage: node tools/process_profiled_wav.js voice-profile.wav challenge.wav processed.wav [profile.json]');
  process.exit(2);
}

const profileAudio = decodePcm16Wav(fs.readFileSync(profilePath));
const challenge = decodePcm16Wav(fs.readFileSync(inputPath));
if (profileAudio.sampleRate !== 48000 || challenge.sampleRate !== 48000) throw new Error('Voice Profile and challenge WAV files must both be 48 kHz PCM16');

const engine = new TaskMivraVoiceEngine({ profileStrength: 0.84, profileFloorDb: -15 });
const profile = engine.enrollVoiceProfile(profileAudio.samples);
const started = process.hrtime.bigint();
const processed = engine.processOffline(challenge.samples);
const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9;
fs.writeFileSync(outputPath, encodePcm16MonoWav(processed, challenge.sampleRate));
if (profileJsonPath) fs.writeFileSync(profileJsonPath, JSON.stringify(profile.toJSON(), null, 2));

console.log(JSON.stringify({
  ...engine.getStatus(),
  profileDurationSeconds: profile.durationSeconds,
  processingSeconds: elapsedSeconds,
  challengeSeconds: challenge.samples.length / challenge.sampleRate,
  realTimeFactor: elapsedSeconds / (challenge.samples.length / challenge.sampleRate),
  rawProfileAudioStored: false,
}, null, 2));
