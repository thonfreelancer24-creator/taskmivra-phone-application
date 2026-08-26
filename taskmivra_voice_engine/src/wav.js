/** Minimal dependency-free PCM16 WAV I/O for local benchmarks. */

export function decodePcm16Wav(buffer) {
  if (!Buffer.isBuffer(buffer)) buffer = Buffer.from(buffer);
  if (buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') {
    throw new Error('Invalid WAV container');
  }

  let offset = 12;
  let channels = 0;
  let sampleRate = 0;
  let bits = 0;
  let format = 0;
  let data = null;

  while (offset + 8 <= buffer.length) {
    const id = buffer.toString('ascii', offset, offset + 4);
    const size = buffer.readUInt32LE(offset + 4);
    const start = offset + 8;
    if (id === 'fmt ') {
      format = buffer.readUInt16LE(start);
      channels = buffer.readUInt16LE(start + 2);
      sampleRate = buffer.readUInt32LE(start + 4);
      bits = buffer.readUInt16LE(start + 14);
    } else if (id === 'data') {
      data = buffer.subarray(start, start + size);
      break;
    }
    offset = start + size + (size & 1);
  }

  if (format !== 1 || bits !== 16 || !data) throw new Error('Only PCM16 WAV is supported');
  if (channels < 1 || channels > 8) throw new Error('Unsupported channel count');

  const frameCount = Math.floor(data.length / (2 * channels));
  const samples = new Float32Array(frameCount);
  for (let frame = 0; frame < frameCount; frame += 1) {
    let sum = 0;
    for (let channel = 0; channel < channels; channel += 1) {
      sum += data.readInt16LE((frame * channels + channel) * 2) / 32768;
    }
    samples[frame] = sum / channels;
  }
  return { sampleRate, samples };
}

export function encodePcm16MonoWav(samples, sampleRate = 48000) {
  const source = samples instanceof Float32Array ? samples : Float32Array.from(samples);
  const dataBytes = source.length * 2;
  const buffer = Buffer.alloc(44 + dataBytes);
  buffer.write('RIFF', 0, 'ascii');
  buffer.writeUInt32LE(36 + dataBytes, 4);
  buffer.write('WAVE', 8, 'ascii');
  buffer.write('fmt ', 12, 'ascii');
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36, 'ascii');
  buffer.writeUInt32LE(dataBytes, 40);
  for (let i = 0; i < source.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, source[i]));
    buffer.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(sample * 32767))), 44 + i * 2);
  }
  return buffer;
}
