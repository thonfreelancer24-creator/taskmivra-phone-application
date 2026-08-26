/**
 * TaskMivra Voice Profile v0.2
 * Original, dependency-free speaker profile and frame scoring implementation.
 * Raw enrollment audio is never retained by the profile object.
 */
const EPS = 1e-12;
const PROFILE_VERSION = 1;
const PROFILE_BANDS_HZ = [
  90, 140, 210, 300, 420, 580, 780, 1020, 1320, 1680,
  2100, 2600, 3200, 3900, 4700, 5600, 6600, 7800,
];

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
function nextPow2(v){let n=1;while(n<v)n<<=1;return n;}
function median(values){if(!values.length)return 0;const a=[...values].sort((x,y)=>x-y),m=a.length>>1;return a.length%2?a[m]:(a[m-1]+a[m])/2;}
function quantile(values,q){if(!values.length)return 0;const a=[...values].sort((x,y)=>x-y),p=(a.length-1)*q,l=Math.floor(p),h=Math.ceil(p);return l===h?a[l]:a[l]+(a[h]-a[l])*(p-l);}
function rms(samples){let s=0;for(const x of samples)s+=x*x;return Math.sqrt(s/Math.max(1,samples.length));}
function fft(real, imag){
  const n=real.length;
  if((n&(n-1))!==0)throw new Error('FFT length must be power of two');
  for(let i=1,j=0;i<n;i++){
    let bit=n>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;
    if(i<j){[real[i],real[j]]=[real[j],real[i]];[imag[i],imag[j]]=[imag[j],imag[i]];}
  }
  for(let len=2;len<=n;len<<=1){
    const angle=-2*Math.PI/len,wr0=Math.cos(angle),wi0=Math.sin(angle);
    for(let off=0;off<n;off+=len){
      let wr=1,wi=0;
      for(let j=0;j<(len>>1);j++){
        const e=off+j,o=e+(len>>1),vr=real[o]*wr-imag[o]*wi,vi=real[o]*wi+imag[o]*wr,ur=real[e],ui=imag[e];
        real[e]=ur+vr;imag[e]=ui+vi;real[o]=ur-vr;imag[o]=ui-vi;
        const nw=wr*wr0-wi*wi0;wi=wr*wi0+wi*wr0;wr=nw;
      }
    }
  }
}

function spectralVector(samples, sampleRate){
  const fftSize=nextPow2(samples.length),real=new Float64Array(fftSize),imag=new Float64Array(fftSize);
  for(let i=0;i<samples.length;i++){
    const w=.5-.5*Math.cos(2*Math.PI*i/Math.max(1,samples.length-1));
    real[i]=samples[i]*w;
  }
  fft(real,imag);
  const bands=new Float64Array(PROFILE_BANDS_HZ.length-1);
  let total=0;
  for(let k=1;k<=fftSize/2;k++){
    const hz=k*sampleRate/fftSize;
    if(hz<PROFILE_BANDS_HZ[0]||hz>=PROFILE_BANDS_HZ.at(-1))continue;
    let b=0;while(b+1<PROFILE_BANDS_HZ.length&&hz>=PROFILE_BANDS_HZ[b+1])b++;
    if(b>=bands.length)continue;
    const p=real[k]*real[k]+imag[k]*imag[k];bands[b]+=p;total+=p;
  }
  const logs=new Float64Array(bands.length);
  let mean=0;
  for(let i=0;i<bands.length;i++){logs[i]=Math.log((bands[i]+EPS)/(total+EPS));mean+=logs[i];}
  mean/=logs.length;
  let norm=0;
  for(let i=0;i<logs.length;i++){logs[i]-=mean;norm+=logs[i]*logs[i];}
  norm=Math.sqrt(norm)+EPS;
  for(let i=0;i<logs.length;i++)logs[i]/=norm;
  return logs;
}

function pitchCandidates(samples, sampleRate){
  const stride=Math.max(1,Math.round(sampleRate/8000)),n=Math.floor(samples.length/stride);
  if(n<80)return [];
  const x=new Float64Array(n);let mean=0;
  for(let i=0;i<n;i++){x[i]=samples[i*stride];mean+=x[i];}mean/=n;
  let energy=0;for(let i=0;i<n;i++){x[i]-=mean;energy+=x[i]*x[i];}
  if(energy<1e-8)return [];
  const rate=sampleRate/stride,minLag=Math.max(2,Math.floor(rate/340)),maxLag=Math.min(n-3,Math.ceil(rate/70));
  const corr=[];
  for(let lag=minLag;lag<=maxLag;lag++){
    let ab=0,aa=0,bb=0;
    for(let i=0;i<n-lag;i++){const a=x[i],b=x[i+lag];ab+=a*b;aa+=a*a;bb+=b*b;}
    corr.push({lag,value:ab/Math.sqrt(Math.max(EPS,aa*bb))});
  }
  const peaks=[];
  for(let i=1;i<corr.length-1;i++){
    if(corr[i].value>=corr[i-1].value&&corr[i].value>=corr[i+1].value&&corr[i].value>.12){
      peaks.push({hz:rate/corr[i].lag,harmonicity:clamp(corr[i].value,0,1)});
    }
  }
  peaks.sort((a,b)=>b.harmonicity-a.harmonicity);
  return peaks.slice(0,6);
}

function cosine(a,b){let s=0;for(let i=0;i<Math.min(a.length,b.length);i++)s+=a[i]*b[i];return clamp(s,-1,1);}
function pitchCloseness(hz,profile){
  if(!hz||!profile.pitchMedianHz)return 0;
  const ratio=Math.abs(Math.log(hz/profile.pitchMedianHz));
  const observed=Math.max(Math.abs(Math.log(Math.max(1,profile.pitchHighHz)/profile.pitchMedianHz)),Math.abs(Math.log(Math.max(1,profile.pitchLowHz)/profile.pitchMedianHz)));const span=Math.max(.075,observed+.05);
  return Math.exp(-0.5*(ratio/span)**2);
}

export class TaskMivraVoiceProfile {
  constructor(data){
    if(!data||data.version!==PROFILE_VERSION)throw new Error('Unsupported TaskMivra Voice Profile version');
    this.version=PROFILE_VERSION;
    this.sampleRate=data.sampleRate;
    this.durationSeconds=data.durationSeconds;
    this.spectralMean=Float64Array.from(data.spectralMean);
    this.spectralSpread=Float64Array.from(data.spectralSpread);
    this.pitchMedianHz=data.pitchMedianHz;
    this.pitchLowHz=data.pitchLowHz;
    this.pitchHighHz=data.pitchHighHz;
    this.harmonicityMean=data.harmonicityMean;
    this.frameCount=data.frameCount;
    Object.freeze(this);
  }
  toJSON(){return{version:this.version,sampleRate:this.sampleRate,durationSeconds:this.durationSeconds,spectralMean:[...this.spectralMean],spectralSpread:[...this.spectralSpread],pitchMedianHz:this.pitchMedianHz,pitchLowHz:this.pitchLowHz,pitchHighHz:this.pitchHighHz,harmonicityMean:this.harmonicityMean,frameCount:this.frameCount};}
  static fromJSON(data){return new TaskMivraVoiceProfile(data);}
}

export function enrollTaskMivraVoiceProfile(input,sampleRate=48000){
  if(sampleRate!==48000)throw new Error('Voice Profile v0.2 requires 48 kHz mono PCM');
  const samples=input instanceof Float32Array?input:Float32Array.from(input),duration=samples.length/sampleRate;
  if(duration<3||duration>5.05)throw new Error('Voice Profile must be 3–5 seconds');
  const frameSize=960,hop=480,frames=[],pitches=[],harmonicities=[];
  let maxRms=0;
  for(let o=0;o+frameSize<=samples.length;o+=hop)maxRms=Math.max(maxRms,rms(samples.subarray(o,o+frameSize)));
  const floor=Math.max(.003,maxRms*.10);
  for(let o=0;o+frameSize<=samples.length;o+=hop){
    const frame=samples.subarray(o,o+frameSize),level=rms(frame);if(level<floor)continue;
    const spectrum=spectralVector(frame,sampleRate),candidates=pitchCandidates(frame,sampleRate),best=candidates[0];
    frames.push(spectrum);
    if(best&&best.harmonicity>.18){pitches.push(best.hz);harmonicities.push(best.harmonicity);}
  }
  if(frames.length<30)throw new Error('Voice Profile needs more clear speech; too few usable frames');
  const mean=new Float64Array(frames[0].length),spread=new Float64Array(frames[0].length);
  for(const f of frames)for(let i=0;i<f.length;i++)mean[i]+=f[i];
  for(let i=0;i<mean.length;i++)mean[i]/=frames.length;
  let norm=0;for(const x of mean)norm+=x*x;norm=Math.sqrt(norm)+EPS;for(let i=0;i<mean.length;i++)mean[i]/=norm;
  for(const f of frames)for(let i=0;i<f.length;i++){const d=f[i]-mean[i];spread[i]+=d*d;}
  for(let i=0;i<spread.length;i++)spread[i]=Math.sqrt(spread[i]/frames.length)+.08;
  const pitchMedian=median(pitches),pitchLow=pitches.length?quantile(pitches,.10):0,pitchHigh=pitches.length?quantile(pitches,.90):0;
  return new TaskMivraVoiceProfile({version:PROFILE_VERSION,sampleRate,durationSeconds:duration,spectralMean:[...mean],spectralSpread:[...spread],pitchMedianHz:pitchMedian,pitchLowHz:pitchLow,pitchHighHz:pitchHigh,harmonicityMean:harmonicities.length?harmonicities.reduce((a,b)=>a+b,0)/harmonicities.length:0,frameCount:frames.length});
}

export function scoreTaskMivraSpeakerFrame(frame,profile,sampleRate=48000){
  if(!(profile instanceof TaskMivraVoiceProfile))throw new TypeError('TaskMivra Voice Profile required');
  const spectrum=spectralVector(frame,sampleRate);let z2=0;for(let i=0;i<spectrum.length;i++){const d=(spectrum[i]-profile.spectralMean[i])/Math.max(.08,profile.spectralSpread[i]);z2+=d*d;}z2/=spectrum.length;const distributionSimilarity=Math.exp(-.5*z2);const cos=cosine(spectrum,profile.spectralMean);const cosineSimilarity=clamp((cos-.50)/.50,0,1);const spectral=clamp(.65*distributionSimilarity+.35*cosineSimilarity,0,1);
  const candidates=pitchCandidates(frame,sampleRate);
  let pitchScore=0,targetPitchHz=0,targetHarmonicity=0;
  for(const c of candidates){const s=c.harmonicity*pitchCloseness(c.hz,profile);if(s>pitchScore){pitchScore=s;targetPitchHz=c.hz;targetHarmonicity=c.harmonicity;}}
  const level=rms(frame),voiced=targetHarmonicity>.15;
  // Spectral identity remains dominant so unvoiced consonants are not hard-gated.
  const confidence=clamp(voiced?.72*spectral+.28*pitchScore:.90*spectral+.10*pitchScore,0,1);
  return{confidence,spectralSimilarity:spectral,pitchSimilarity:pitchScore,targetPitchHz,targetHarmonicity,level};
}

export function taskMivraProfileBandAffinity(power,fftSize,sampleRate,profile){
  const bands=new Float64Array(profile.spectralMean.length);let total=0;
  for(let k=1;k<power.length;k++){
    const hz=k*sampleRate/fftSize;if(hz<PROFILE_BANDS_HZ[0]||hz>=PROFILE_BANDS_HZ.at(-1))continue;
    let b=0;while(b+1<PROFILE_BANDS_HZ.length&&hz>=PROFILE_BANDS_HZ[b+1])b++;
    if(b>=bands.length)continue;bands[b]+=power[k];total+=power[k];
  }
  const logs=new Float64Array(bands.length);let mean=0;
  for(let i=0;i<bands.length;i++){logs[i]=Math.log((bands[i]+EPS)/(total+EPS));mean+=logs[i];}mean/=logs.length;
  let norm=0;for(let i=0;i<logs.length;i++){logs[i]-=mean;norm+=logs[i]*logs[i];}norm=Math.sqrt(norm)+EPS;for(let i=0;i<logs.length;i++)logs[i]/=norm;
  const affinities=new Float64Array(bands.length);
  for(let i=0;i<bands.length;i++){const d=Math.abs(logs[i]-profile.spectralMean[i])/profile.spectralSpread[i];affinities[i]=Math.exp(-.5*d*d);}
  return{affinities,edges:PROFILE_BANDS_HZ};
}
