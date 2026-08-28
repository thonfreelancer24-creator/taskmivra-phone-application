from __future__ import annotations
import json, shutil, subprocess, urllib.parse, urllib.request
from pathlib import Path

SR=48000
SOURCES=[
("john_gonzales","John Gonzales","LibriVox_-_A_Modest_Proposal.ogg","train"),
("betsie_bush","Betsie Bush","LibriVox_-_The_Case_of_Lady_Sannox.ogg","train"),
("william_coon","William Coon","LibriVox_-_The_Red_Room_by_H._G._Wells.ogg","train"),
("catharine_eastman","Catharine Eastman","Ransom_red_chief_henry_ce.ogg","train"),
("david_federman","David Federman","Gs006_hauntedhouse_woolf_dgf.ogg","train"),
("rebecca_snyder","Rebecca Snyder","Sleeping_beauty_in_the_wood_perrault_rjs.ogg","train"),
("james_christopher","James Christopher","Shortstory026_goodmatch_jc.ogg","train"),
("kristen_mcquillin","Kristen McQuillin","LibriVox_-_Constitution_of_the_United_States_of_America_03.ogg","train"),
("virgil","Virgil","Gs006_redroom_wells_v.ogg","train"),
("lady_maria","Lady Maria","Morella_poe_mt.ogg","train"),
("lola_rogers","Lola Rogers","Yellow_wallpaper_gilman_lr.ogg","heldout"),
("john_garvin","John Garvin","LibriVox_-_Peter_and_Wendy_17.ogg","heldout"),
]

def url(fn): return "https://commons.wikimedia.org/wiki/Special:Redirect/file/"+urllib.parse.quote(fn,safe="")
def page(fn): return "https://commons.wikimedia.org/wiki/File:"+fn

def get(u,p):
    if p.exists() and p.stat().st_size>10000: return
    req=urllib.request.Request(u,headers={"User-Agent":"TaskMivraVoice/0.5 rights-clean training"})
    with urllib.request.urlopen(req,timeout=120) as r,p.open("wb") as f: shutil.copyfileobj(r,f)
    if p.stat().st_size < 10000: raise RuntimeError(f"download too small: {p}")

def ff(src,dst,tv=False,duration=120):
    cmd=["ffmpeg","-y","-v","error","-ss","8","-t",str(duration),"-i",str(src),"-ac","1","-ar",str(SR)]
    if tv: cmd += ["-af","highpass=f=170,lowpass=f=6800,equalizer=f=2500:t=q:w=1.2:g=2.5,acompressor=threshold=-20dB:ratio=3:attack=15:release=180"]
    cmd += ["-c:a","pcm_s16le",str(dst)]; subprocess.run(cmd,check=True)

def main():
    root=Path("taskmivra_voice_engine/ml/v05_data"); src=root/"source"; wav=root/"wav"; out=root/"heldout"
    for d in (src,wav,out): d.mkdir(parents=True,exist_ok=True)
    prov=[]; train=[]
    for sid,reader,fn,split in SOURCES:
        raw=src/(sid+Path(fn).suffix); clean=wav/(sid+".wav"); tv=wav/(sid+"_tv.wav")
        du=url(fn); print("DOWNLOAD",reader,du,flush=True); get(du,raw)
        ff(raw,clean,False); ff(raw,tv,True)
        prov.append({"id":sid,"reader":reader,"filename":fn,"source_page":page(fn),"download_url":du,"rights":"public-domain LibriVox recording","split":split})
        if split=="heldout": ff(raw,out/(sid+"_profile.wav"),False,12)
        else: train.append((sid,clean,tv))
    rows=[]; seed=0
    for tid,tclean,_ in train:
        for oid,oclean,otv in train:
            if tid==oid: continue
            for rep in range(3):
                seed+=1
                rows.append({
                    "target_clean":str(tclean),"profile_clean":str(tclean),"interference":str(otv),
                    "negative_profile_clean":str(oclean),"crop_seed":seed,"derived_from_benchmark_output":False,
                    "rights":{"target_clean":"public-domain","profile_clean":"public-domain","interference":"public-domain","negative_profile_clean":"public-domain"},
                    "source_ids":{"target":tid,"interferer":oid},"tv_treatment":True
                })
    manifest=root/"train_manifest.jsonl"; manifest.write_text("\n".join(json.dumps(r) for r in rows)+"\n",encoding="utf-8")
    (root/"provenance.json").write_text(json.dumps(prov,indent=2),encoding="utf-8")
    print(json.dumps({"training_rows":len(rows),"train_speakers":len(train),"heldout_speakers":2,"manifest":str(manifest)}),flush=True)
if __name__=="__main__": main()
