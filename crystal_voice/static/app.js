const $ = id => document.getElementById(id);
let activeCapture = null;
let profileObjectUrl = null;
let profileReady = false;

function microphoneError(error) {
  const name = error?.name || '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'Microphone access is blocked. Allow microphone access for this browser, then reload the page.';
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') return 'No microphone was detected on this Mac.';
  if (name === 'NotReadableError' || name === 'TrackStartError') return 'The microphone is busy or unavailable. Close another app that may be using it and try again.';
  return error?.message || 'Unable to start microphone recording.';
}

function clearChallengeResults() {
  $('results').hidden = true;
  for (const id of ['raw', 'isolation', 'processed']) {
    const player = $(id);
    player.pause();
    player.removeAttribute('src');
    player.load();
  }
  $('metrics').innerHTML = '';
}

async function wavRecording(owner, startButton, stopButton, seconds, status) {
  if (activeCapture) throw new Error('Another recording is already active. Stop it first.');
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    throw new Error('Open Crystal Voice at http://127.0.0.1 in Chrome or Safari. Microphone recording may not work inside an embedded preview.');
  }

  let stream;
  let context;
  try {
    status.textContent = 'Requesting microphone access…';
    stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false}});
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) throw new Error('This browser does not support Web Audio recording.');
    context = new AudioContextClass({sampleRate:48000});
    if (context.state === 'suspended') await context.resume();

    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096,1,1);
    const silent = context.createGain();
    silent.gain.value = 0;
    const chunks = [];
    processor.onaudioprocess = event => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    source.connect(processor);
    processor.connect(silent);
    silent.connect(context.destination);

    let elapsed = 0;
    let timer;
    let finished = false;
    let resolveRecording;
    const recording = new Promise(resolve => { resolveRecording = resolve; });

    const stop = () => {
      if (finished) return;
      finished = true;
      clearInterval(timer);
      processor.onaudioprocess = null;
      try { processor.disconnect(); } catch (_) {}
      try { source.disconnect(); } catch (_) {}
      try { silent.disconnect(); } catch (_) {}
      stream.getTracks().forEach(track => track.stop());
      const rate = context.sampleRate;
      context.close().catch(() => {});
      activeCapture = null;
      startButton.disabled = false;
      stopButton.hidden = true;

      const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
      if (!length) {
        status.textContent = 'No audio samples were captured. Check the browser microphone permission and selected input device.';
        resolveRecording(null);
        return;
      }
      const pcm = new Float32Array(length);
      let offset = 0;
      for (const chunk of chunks) { pcm.set(chunk, offset); offset += chunk.length; }
      resolveRecording(encodeWav(pcm, rate));
    };

    activeCapture = {owner, stop};
    startButton.disabled = true;
    stopButton.hidden = false;
    status.textContent = `Recording 0.0 / ${seconds}s maximum`;
    timer = setInterval(() => {
      elapsed += 0.1;
      status.textContent = `Recording ${elapsed.toFixed(1)} / ${seconds}s maximum`;
      if (elapsed >= seconds) stop();
    }, 100);
    return await recording;
  } catch (error) {
    stream?.getTracks().forEach(track => track.stop());
    context?.close().catch(() => {});
    activeCapture = null;
    startButton.disabled = false;
    stopButton.hidden = true;
    throw new Error(microphoneError(error));
  }
}

function encodeWav(samples, rate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2), view = new DataView(buffer);
  const text = (offset, value) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt()));
  text(0,'RIFF'); view.setUint32(4,36+samples.length*2,true); text(8,'WAVEfmt '); view.setUint32(16,16,true);
  view.setUint16(20,1,true); view.setUint16(22,1,true); view.setUint32(24,rate,true); view.setUint32(28,rate*2,true);
  view.setUint16(32,2,true); view.setUint16(34,16,true); text(36,'data'); view.setUint32(40,samples.length*2,true);
  samples.forEach((sample,index)=>view.setInt16(44+index*2,Math.max(-32768,Math.min(32767,Math.round(sample*32767))),true));
  return buffer;
}

async function send(path, wav) {
  const response = await fetch(path,{method:'POST',headers:{'Content-Type':'audio/wav'},body:wav});
  const json = await response.json();
  if (!response.ok) throw Error(json.error);
  return json;
}

$('enrollStop').onclick = () => { if (activeCapture?.owner === 'enroll') activeCapture.stop(); };
$('challengeStop').onclick = () => { if (activeCapture?.owner === 'challenge') activeCapture.stop(); };

$('enroll').onclick = async () => {
  try {
    const wav = await wavRecording('enroll',$('enroll'),$('enrollStop'),5,$('enrollStatus'));
    if (!wav) return;
    if (profileObjectUrl) URL.revokeObjectURL(profileObjectUrl);
    profileObjectUrl = URL.createObjectURL(new Blob([wav],{type:'audio/wav'}));
    $('profilePlayback').src = profileObjectUrl;
    $('profilePlayback').hidden = false;
    $('enrollStatus').textContent = 'Saving target voice profile…';
    const json = await send('/api/enroll',wav);
    profileReady = true;
    $('enrollStatus').textContent = `Profile ready · ${json.duration_seconds.toFixed(2)}s · SHA-256 ${json.sha256.slice(0,12)}…`;
    $('challenge').disabled = false;
    $('challenge').textContent = 'Record challenge';
    $('enroll').textContent = 'Re-record profile';
    clearChallengeResults();
  } catch (error) {
    $('enrollStatus').textContent = error.message;
  }
};

$('challenge').onclick = async () => {
  if (!profileReady) {
    $('challengeStatus').textContent = 'Record a Target Voice Profile first.';
    $('challenge').disabled = true;
    return;
  }

  clearChallengeResults();
  try {
    const wav = await wavRecording('challenge',$('challenge'),$('challengeStop'),8,$('challengeStatus'));
    if (!wav) return;

    $('challenge').disabled = true;
    $('challengeStatus').textContent = 'Extracting, cleaning, and restoring target speaker…';
    const json = await send('/api/process',wav);

    $('challenge').textContent = 'Record another challenge';
    $('challengeStatus').textContent = json.same_take_verified ? 'Ready for another challenge · all three source fingerprints verified' : 'VERIFICATION FAILED';
    $('results').hidden = false;
    const stamp = Date.now();
    $('raw').src = '/audio/raw.wav?' + stamp;
    $('isolation').src = '/audio/isolation.wav?' + stamp;
    $('processed').src = '/audio/processed.wav?' + stamp;
    $('metrics').innerHTML = Object.entries({capture:json.capture_id.slice(0,16)+'…',model:json.model,conditioned:json.conditioned_by_reference,raw_peak:json.raw_peak_dbfs.toFixed(2)+' dBFS',isolation_peak:json.isolation_peak_dbfs.toFixed(2)+' dBFS',candidate_peak:json.processed_peak_dbfs.toFixed(2)+' dBFS',clipped:json.clipped_samples,RTF:json.real_time_factor.toFixed(3),candidate_attenuation:json.attenuation_db.toFixed(2)+' dB'}).map(([key,value])=>`<div class=metric>${key}<br><strong>${value}</strong></div>`).join('');
    $('results').scrollIntoView({behavior:'smooth',block:'start'});
  } catch (error) {
    $('challengeStatus').textContent = error.message;
  } finally {
    $('challenge').disabled = !profileReady;
  }
};

async function refreshStatus() {
  try {
    const response = await fetch('/api/status',{cache:'no-store'});
    const json = await response.json();
    $('ready').textContent = json.ready ? 'MODEL READY' : 'NOT READY';
    $('version').textContent = json.version;
    $('ready').title = json.model + ' ' + json.model_version;
    profileReady = Boolean(json.profile_ready);
    $('challenge').disabled = !profileReady;
    if (profileReady) {
      $('enroll').textContent = 'Re-record profile';
      $('enrollStatus').textContent = 'Target Voice Profile is still ready in this session.';
      $('challenge').textContent = 'Record challenge';
    }
  } catch (_) {
    $('ready').textContent = 'STARTUP ERROR';
  }
}

refreshStatus();
