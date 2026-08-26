import test from 'node:test';
import assert from 'node:assert/strict';
import { TaskMivraVoiceEngine } from '../src/voice_engine.js';

function rms(samples,start=0){let sum=0;for(let i=start;i<samples.length;i++)sum+=samples[i]*samples[i];return Math.sqrt(sum/Math.max(1,samples.length-start));}
function correlation(a,b){let ab=0,aa=0,bb=0;for(let i=0;i<Math.min(a.length,b.length);i++){ab+=a[i]*b[i];aa+=a[i]*a[i];bb+=b[i]*b[i];}return ab/Math.sqrt(Math.max(1e-12,aa*bb));}
function deterministicNoise(length,amplitude=.08){const out=new Float32Array(length);let state=0x12345678;for(let i=0;i<length;i++){state=(1664525*state+1013904223)>>>0;out[i]=(((state/0xffffffff)*2)-1)*amplitude;}return out;}

test('bypass preserves physical microphone samples',()=>{const e=new TaskMivraVoiceEngine({enabled:false}),input=Float32Array.from([.2,-.4,.1,0]);assert.deepEqual([...e.process(input)],[...input]);});
test('reports bounded streaming latency and no external voice model',()=>{const s=new TaskMivraVoiceEngine().getStatus();assert.equal(s.sampleRate,48000);assert.ok(s.algorithmicLatencyMs<=10.1);assert.equal(s.externalVoiceModel,false);});
test('offline processing preserves duration and ceiling',()=>{const rate=48000,input=new Float32Array(rate);for(let i=0;i<input.length;i++)input[i]=.95*Math.sin(2*Math.PI*440*i/rate);const out=new TaskMivraVoiceEngine().processOffline(input);assert.equal(out.length,input.length);const peak=out.reduce((m,x)=>Math.max(m,Math.abs(x)),0);assert.ok(peak<=10**(-3/20)+1e-5);});
test('stationary broadband noise is reduced after estimator warm-up',()=>{const rate=48000,input=deterministicNoise(rate*2,.08),out=new TaskMivraVoiceEngine().processOffline(input);assert.ok(rms(out,rate)<rms(input,rate)*.80);});
test('speech-band reference remains recognizable in noise',()=>{const rate=48000,length=rate*2,noise=deterministicNoise(length,.05),clean=new Float32Array(length),mix=new Float32Array(length);for(let i=0;i<length;i++){clean[i]=.18*Math.sin(2*Math.PI*700*i/rate)+.08*Math.sin(2*Math.PI*1900*i/rate);mix[i]=clean[i]+noise[i];}const out=new TaskMivraVoiceEngine().processOffline(mix);assert.ok(correlation(out.subarray(rate/2),clean.subarray(rate/2))>.80);});
