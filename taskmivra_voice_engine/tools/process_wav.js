#!/usr/bin/env node
import fs from 'node:fs';
import { TaskMivraVoiceEngine } from '../src/voice_engine.js';
import { decodePcm16Wav, encodePcm16MonoWav } from '../src/wav.js';

const [inputPath, outputPath] = process.argv.slice(2);
if (!inputPath || !outputPath) {
  console.error('Usage: node tools/process_wav.js input.wav output.wav');
  process.exit(2);
}

const decoded = decodePcm16Wav(fs.readFileSync(inputPath));
if (decoded.sampleRate !== 48000) {
  throw new Error(`Expected 48 kHz input, got ${decoded.sampleRate} Hz`);
}
const engine = new TaskMivraVoiceEngine();
const processed = engine.processOffline(decoded.samples);
fs.writeFileSync(outputPath, encodePcm16MonoWav(processed, decoded.sampleRate));
console.log(JSON.stringify(engine.getStatus(), null, 2));
