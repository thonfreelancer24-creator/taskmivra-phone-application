/** TaskMivra Voice Engine v0.3 — owned streaming DSP + profile-conditioned control. */
import {
  TaskMivraVoiceProfile,
  enrollTaskMivraVoiceProfile,
  scoreTaskMivraSpeakerFrame,
  taskMivraProfileBandAffinity,
} from './speaker_profile.js';
const EPS = 1e-12;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
function nextPow2(v){let n=1;while(n<v)n<<=1;return n;}
function fft(real, imag, inverse=false){const n=real.length;if((n&(n-1))!==0)throw new Error('FFT length must be power of two');for(let i=1,j=0;i<n;i++){let bit=n>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j){[real[i],real[j]]=[real[j],real[i]];[imag[i],imag[j]]=[imag[j],imag[i]];}}for(let len=2;len<=n;len<<=1){const a=(inverse?2:-2)*Math.PI/len,wr0=Math.cos(a),wi0=Math.sin(a);for(let off=0;off<n;off+=len){let wr=1,wi=0;for(let j=0;j<(len>>1);j++){const e=off+j,o=e+(len>>1),vr=real[o]*wr-imag[o]*wi,vi=real[o]*wi+imag[o]*wr,ur=real[e],ui=imag[e];real[e]=ur+vr;imag[e]=ui+vi;real[o]=ur-vr;imag[o]=ui-vi;const nw=wr*wr0-wi*wi0;wi=wr*wi0+wi*wr0;wr=nw;}}}if(inverse){for(let i=0;i<n;i++){real[i]/=n;imag[i]/=n;}}}
export class TaskMivraVoiceEngine {
  constructor(options={}){this.sampleRate=options.sampleRate??48000;if(this.sampleRate!==48000)throw new Error('v0.3 requires 48 kHz mono');this.hopSize=480;this.frameSize=960;this.fftSize=nextPow2(this.frameSize);this.binCount=this.fftSize/2+1;this.enabled=options.enabled??true;this.ceiling=10**((options.ceilingDbfs??-3)/20);this.maxAutoGain=10**((options.maxAutoGainDb??3)/20);this.autoGainEnabled=options.autoGainEnabled??false;this.window=new Float64Array(this.frameSize);for(let i=0;i<this.frameSize;i++)this.window[i]=Math.sin(Math.PI*(i+.5)/this.frameSize);this.history=new Float64Array(this.frameSize);this.ola=new Float64Array(this.frameSize);this.prevGain=new Float64Array(this.binCount);this.prevGain.fill(1);this.noisePsd=new Float64Array(this.binCount);this.smoothPsd=new Float64Array(this.binCount);this.minimumPsd=new Float64Array(this.binCount);this.minimumPsd.fill(Infinity);this.inputFifo=[];this.outputFifo=[];this.inputRead=0;this.outputRead=0;this.hpPrevX=0;this.hpPrevY=0;const rc=1/(2*Math.PI*70),dt=1/this.sampleRate;this.hpAlpha=rc/(rc+dt);this.frameCounter=0;this.noiseInitialized=false;this.gainRecovery=1;this.limiterGain=1;this.failSafeTriggered=false;this.lastError=null;this.lastInputPeak=0;this.lastOutputPeak=0;this.voiceProfile=null;this.targetConfidence=1;this.targetSpeakerGain=1;this.targetPitchHz=0;this.profileStrength=clamp(options.profileStrength??1,0,1);this.profileFloor=10**((options.profileFloorDb??-30)/20);this.profileTargetBoost=10**((options.profileTargetBoostDb??2.6)/20);}
  getLatencySamples(){return this.hopSize;}
  getLatencyMs(){return 1000*this.hopSize/this.sampleRate;}
  setEnabled(v){this.enabled=Boolean(v);}
  enrollVoiceProfile(samples){const profile=enrollTaskMivraVoiceProfile(samples,this.sampleRate);this.setVoiceProfile(profile);return profile;}
  setVoiceProfile(profile){this.voiceProfile=profile instanceof TaskMivraVoiceProfile?profile:TaskMivraVoiceProfile.fromJSON(profile);this.targetConfidence=.20;this.targetSpeakerGain=this.profileFloor;this.targetPitchHz=0;}
  clearVoiceProfile(){this.voiceProfile=null;this.targetConfidence=1;this.targetSpeakerGain=1;this.targetPitchHz=0;}
  getStatus(){return{ready:true,enabled:this.enabled,sampleRate:this.sampleRate,frameMs:20,hopMs:10,algorithmicLatencyMs:this.getLatencyMs(),processedFrames:this.frameCounter,failSafeTriggered:this.failSafeTriggered,lastError:this.lastError,lastInputPeak:this.lastInputPeak,lastOutputPeak:this.lastOutputPeak,externalVoiceModel:false,voiceProfileReady:Boolean(this.voiceProfile),targetConfidence:this.targetConfidence,targetSpeakerGain:this.targetSpeakerGain,targetPitchHz:this.targetPitchHz};}
  _hp(x){const y=this.hpAlpha*(this.hpPrevY+x-this.hpPrevX);this.hpPrevX=x;this.hpPrevY=y;return y;}
  _gain(power,k){if(!this.noiseInitialized)return 1;const noise=Math.max(this.noisePsd[k],EPS),post=power/noise,w=Math.sqrt(Math.max(0,1-1/Math.max(post,1))),hz=k*this.sampleRate/this.fftSize,floor=hz>=180&&hz<=5200?.22:.10,speech=clamp((post-2)/6,0,1);let target=Math.max(floor,w);if(speech>0){target=Math.max(target,.50);target=target*(1-.22*speech)+.22*speech;}const prev=this.prevGain[k],alpha=target<prev?.90:.45,sm=alpha*prev+(1-alpha)*target;this.prevGain[k]=sm;return sm;}
  _noise(power){for(let k=0;k<this.binCount;k++){const p=power[k];if(!this.noiseInitialized){this.smoothPsd[k]=p;this.noisePsd[k]=Math.max(p*.5,EPS);this.minimumPsd[k]=p;continue;}const sm=.82*this.smoothPsd[k]+.18*p;this.smoothPsd[k]=sm;this.minimumPsd[k]=Math.min(this.minimumPsd[k],sm);const post=p/Math.max(this.noisePsd[k],EPS);this.noisePsd[k]=post<3?.86*this.noisePsd[k]+.14*p:.998*this.noisePsd[k]+.002*p;}if(!this.noiseInitialized)this.noiseInitialized=true;if(this.frameCounter>0&&this.frameCounter%50===0){for(let k=0;k<this.binCount;k++){const m=Number.isFinite(this.minimumPsd[k])?this.minimumPsd[k]:this.smoothPsd[k],c=Math.max(m*1.25,EPS);this.noisePsd[k]=.75*this.noisePsd[k]+.25*c;this.minimumPsd[k]=this.smoothPsd[k];}}}
  _post(samples){let ss=0,peak=0;for(const x of samples){ss+=x*x;peak=Math.max(peak,Math.abs(x));}const rms=Math.sqrt(ss/Math.max(samples.length,1)),target=10**(-26/20),req=this.autoGainEnabled&&rms>EPS?clamp(target/rms,1,this.maxAutoGain):1;this.gainRecovery=.995*this.gainRecovery+.005*req;const pg=peak*this.gainRecovery,lt=pg>this.ceiling?this.ceiling/pg:1;if(lt<this.limiterGain)this.limiterGain=lt;else this.limiterGain=Math.min(1,this.limiterGain+.01);const gain=this.gainRecovery*this.limiterGain;let op=0;for(let i=0;i<samples.length;i++){samples[i]*=gain;if(Math.abs(samples[i])>this.ceiling)samples[i]=Math.sign(samples[i])*this.ceiling;op=Math.max(op,Math.abs(samples[i]));}this.lastOutputPeak=op;}
  _hop(chunk){
    this.history.copyWithin(0,this.hopSize);this.history.set(chunk,this.frameSize-this.hopSize);
    let speaker=null,profileBands=null;
    if(this.voiceProfile){
      const frame=Float32Array.from(this.history);
      speaker=scoreTaskMivraSpeakerFrame(frame,this.voiceProfile,this.sampleRate);
      const rise=speaker.confidence>this.targetConfidence?.42:.90;
      this.targetConfidence=rise*this.targetConfidence+(1-rise)*speaker.confidence;
      this.targetPitchHz=speaker.targetPitchHz||0;
      const x=clamp((this.targetConfidence-.25)/.20,0,1),smooth=x*x*(3-2*x),desired=this.profileFloor+(this.profileTargetBoost-this.profileFloor)*smooth;
      const desiredBlended=1-this.profileStrength*(1-desired),gainAlpha=desiredBlended>this.targetSpeakerGain?.28:.95;
      this.targetSpeakerGain=gainAlpha*this.targetSpeakerGain+(1-gainAlpha)*desiredBlended;
    }
    const real=new Float64Array(this.fftSize),imag=new Float64Array(this.fftSize);
    for(let i=0;i<this.frameSize;i++)real[i]=this.history[i]*this.window[i];fft(real,imag);
    const power=new Float64Array(this.binCount);for(let k=0;k<this.binCount;k++)power[k]=real[k]*real[k]+imag[k]*imag[k]+EPS;
    this._noise(power);
    if(this.voiceProfile)profileBands=taskMivraProfileBandAffinity(power,this.fftSize,this.sampleRate,this.voiceProfile);
    const gains=new Float64Array(this.binCount);for(let k=0;k<this.binCount;k++)gains[k]=this._gain(power[k],k);
    for(let k=1;k<this.binCount-1;k++)gains[k]=.25*gains[k-1]+.5*gains[k]+.25*gains[k+1];
    for(let k=0;k<this.binCount;k++){
      let g=gains[k];
      if(this.voiceProfile&&profileBands){
        const hz=k*this.sampleRate/this.fftSize;let b=-1;
        for(let i=0;i<profileBands.affinities.length;i++){if(hz>=profileBands.edges[i]&&hz<profileBands.edges[i+1]){b=i;break;}}
        const affinity=b>=0?profileBands.affinities[b]:.65;
        const bandMask=.72+.28*affinity;
        let harmonicMask=1;
        if(speaker&&speaker.targetPitchHz>70&&speaker.targetHarmonicity>.18&&hz>=100&&hz<=5200&&this.targetConfidence<.85){
          const f0=speaker.targetPitchHz,h=Math.max(1,Math.round(hz/f0)),distance=Math.abs(hz-h*f0),width=Math.max(42,f0*.20),harmonic=Math.exp(-.5*(distance/width)**2);
          const depth=this.targetConfidence<.35?0.46:0.34;
          harmonicMask=(1-depth)+depth*harmonic;
        }
        const bandIdentity=0.82+0.18*bandMask;
        const highMask=hz>=5200?(.20+.80*affinity):(hz>=3000?(.38+.62*affinity):1);
        const identityMask=bandIdentity*harmonicMask*highMask;
        const profileMask=this.targetSpeakerGain*identityMask;
        const voiceRecovery=clamp((this.targetConfidence-.35)/.25,0,1);
        const bodyRecovery=hz>=100&&hz<300?1+voiceRecovery*.45:(hz>=300&&hz<1000?1+voiceRecovery*.12:1);
        g*=clamp(profileMask*bodyRecovery,this.profileFloor,this.profileTargetBoost*1.25);
      }
      real[k]*=g;imag[k]*=g;if(k>0&&k<this.fftSize/2){const m=this.fftSize-k;real[m]*=g;imag[m]*=g;}
    }
    fft(real,imag,true);for(let i=0;i<this.frameSize;i++)this.ola[i]+=real[i]*this.window[i];
    const out=new Float64Array(this.hopSize);for(let i=0;i<this.hopSize;i++)out[i]=this.ola[i];this.ola.copyWithin(0,this.hopSize);this.ola.fill(0,this.frameSize-this.hopSize);this._post(out);for(const x of out)this.outputFifo.push(x);this.frameCounter++;
  }
  process(input){const src=input instanceof Float32Array?input:Float32Array.from(input);if(!this.enabled)return new Float32Array(src);try{let peak=0;for(const x0 of src){const x=Number.isFinite(x0)?clamp(x0,-1,1):0;peak=Math.max(peak,Math.abs(x));this.inputFifo.push(this._hp(x));}this.lastInputPeak=peak;while(this.inputFifo.length-this.inputRead>=this.hopSize){const c=new Float64Array(this.hopSize);for(let i=0;i<this.hopSize;i++)c[i]=this.inputFifo[this.inputRead+i];this.inputRead+=this.hopSize;this._hop(c);}const out=new Float32Array(src.length);for(let i=0;i<out.length;i++)out[i]=this.outputRead<this.outputFifo.length?this.outputFifo[this.outputRead++]:0;if(this.inputRead>4096){this.inputFifo=this.inputFifo.slice(this.inputRead);this.inputRead=0;}if(this.outputRead>4096){this.outputFifo=this.outputFifo.slice(this.outputRead);this.outputRead=0;}return out;}catch(error){this.failSafeTriggered=true;this.lastError=`${error?.name??'Error'}: ${error?.message??String(error)}`;return new Float32Array(src);}}
  processOffline(input,chunkSize=this.hopSize){const src=input instanceof Float32Array?input:Float32Array.from(input),chunks=[];for(let o=0;o<src.length;o+=chunkSize)chunks.push(this.process(src.subarray(o,Math.min(src.length,o+chunkSize))));chunks.push(this.process(new Float32Array(this.getLatencySamples()+this.hopSize)));const total=chunks.reduce((s,c)=>s+c.length,0),joined=new Float32Array(total);let p=0;for(const c of chunks){joined.set(c,p);p+=c.length;}const d=this.getLatencySamples();return joined.slice(d,d+src.length);}
}
