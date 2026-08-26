import test from 'node:test';
import assert from 'node:assert/strict';
import { enrollTaskMivraVoiceProfile, scoreTaskMivraSpeakerFrame, TaskMivraVoiceProfile } from '../src/speaker_profile.js';
import { TaskMivraVoiceEngine } from '../src/voice_engine.js';

const rate=48000;
function speaker(seconds,f0,formants=[700,1900,3200],amp=.22){
  const n=Math.round(rate*seconds),out=new Float32Array(n);
  for(let i=0;i<n;i++){
    const t=i/rate;let x=0;
    for(let h=1;h<=24;h++){
      const hz=f0*h;if(hz>7600)break;
      let shape=.08;for(const f of formants)shape+=Math.exp(-0.5*((hz-f)/(180+f*.05))**2);
      x+=shape*Math.sin(2*Math.PI*hz*t+(h%3)*.17)/h;
    }
    out[i]=amp*(.78+.22*Math.sin(2*Math.PI*.9*t))*x;
  }
  return out;
}
function correlation(a,b){let ab=0,aa=0,bb=0;for(let i=0;i<Math.min(a.length,b.length);i++){ab+=a[i]*b[i];aa+=a[i]*a[i];bb+=b[i]*b[i];}return ab/Math.sqrt(Math.max(1e-12,aa*bb));}

test('voice profile requires a 3-5 second enrollment',()=>{assert.throws(()=>enrollTaskMivraVoiceProfile(speaker(2.5,125)),/3–5 seconds/);});
test('voice profile stores derived representation, not raw PCM',()=>{const p=enrollTaskMivraVoiceProfile(speaker(4,125));const json=p.toJSON();assert.equal(json.version,1);assert.equal('samples' in json,false);assert.equal('rawAudio' in json,false);assert.ok(json.spectralMean.length>=12);assert.ok(json.frameCount>30);const restored=TaskMivraVoiceProfile.fromJSON(json);assert.equal(restored.pitchMedianHz,p.pitchMedianHz);});
test('enrolled target scores above a mismatched synthetic speaker',()=>{const p=enrollTaskMivraVoiceProfile(speaker(4,125,[650,1750,3000]));const target=speaker(.02,128,[650,1750,3000]);const other=speaker(.02,220,[950,2500,3900]);const a=scoreTaskMivraSpeakerFrame(target,p),b=scoreTaskMivraSpeakerFrame(other,p);assert.ok(a.confidence>b.confidence+.08,`target=${a.confidence} other=${b.confidence}`);});
test('engine accepts, reports and clears the local TaskMivra Voice Profile',()=>{const e=new TaskMivraVoiceEngine(),p=e.enrollVoiceProfile(speaker(4,125,[650,1750,3000]));assert.equal(e.getStatus().voiceProfileReady,true);assert.equal(p.toJSON().samples,undefined);e.clearVoiceProfile();assert.equal(e.getStatus().voiceProfileReady,false);});
test('profile-conditioned processing favors target-like synthetic speech over a mismatched speaker',()=>{const targetProfile=speaker(4,125,[650,1750,3000]);const target=speaker(2,128,[650,1750,3000],.13),other=speaker(2,220,[950,2500,3900],.14),mix=new Float32Array(target.length);for(let i=0;i<mix.length;i++)mix[i]=target[i]+other[i];const plain=new TaskMivraVoiceEngine().processOffline(mix);const profiledEngine=new TaskMivraVoiceEngine({profileStrength:.88,profileFloorDb:-15});profiledEngine.enrollVoiceProfile(targetProfile);const profiled=profiledEngine.processOffline(mix);const start=rate/2;const plainTarget=correlation(plain.subarray(start),target.subarray(start)),plainOther=correlation(plain.subarray(start),other.subarray(start));const profTarget=correlation(profiled.subarray(start),target.subarray(start)),profOther=correlation(profiled.subarray(start),other.subarray(start));assert.ok((profTarget-profOther)>(plainTarget-plainOther)+.02,`plain=${plainTarget-plainOther} profiled=${profTarget-profOther}`);});
test('profile-conditioned target-only speech remains strongly correlated with the enrolled speaker',()=>{const p=speaker(4,125,[650,1750,3000]),target=speaker(2,130,[650,1750,3000],.14);const e=new TaskMivraVoiceEngine({profileStrength:.82,profileFloorDb:-15});e.enrollVoiceProfile(p);const out=e.processOffline(target),start=rate/2;assert.ok(correlation(out.subarray(start),target.subarray(start))>.82);});
test('mismatched speaker is attenuated when a different profile is active',()=>{const p=speaker(4,125,[650,1750,3000]),other=speaker(2,220,[950,2500,3900],.14);const plain=new TaskMivraVoiceEngine().processOffline(other);const e=new TaskMivraVoiceEngine({profileStrength:.9,profileFloorDb:-16});e.enrollVoiceProfile(p);const filtered=e.processOffline(other);const start=rate/2;let a=0,b=0;for(let i=start;i<other.length;i++){a+=plain[i]*plain[i];b+=filtered[i]*filtered[i];}assert.ok(Math.sqrt(b/(other.length-start))<Math.sqrt(a/(other.length-start))*.80);});
