"""Training entry point for TaskMivra-owned target-speaker weights."""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import torch
from torch.utils.data import DataLoader
from dataset import TaskMivraRightsGatedDataset
from model import TaskMivraTargetSpeakerNet


def si_sdr_loss(est,target):
    est=est-est.mean(-1,keepdim=True); target=target-target.mean(-1,keepdim=True)
    scale=(est*target).sum(-1,keepdim=True)/(target.square().sum(-1,keepdim=True)+1e-8)
    proj=scale*target; noise=est-proj
    return -(10*torch.log10((proj.square().sum(-1)+1e-8)/(noise.square().sum(-1)+1e-8))).mean()

def spectral_loss(est,target):
    win=torch.hann_window(960,device=est.device,dtype=est.dtype)
    E=torch.stft(est,1024,480,960,win,return_complex=True); T=torch.stft(target,1024,480,960,win,return_complex=True)
    return (torch.log1p(E.abs())-torch.log1p(T.abs())).abs().mean()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('manifest'); ap.add_argument('--out',default='checkpoints'); ap.add_argument('--epochs',type=int,default=20); ap.add_argument('--batch',type=int,default=4); ap.add_argument('--lr',type=float,default=3e-4); ap.add_argument('--device',default='cuda' if torch.cuda.is_available() else 'cpu'); args=ap.parse_args()
    torch.manual_seed(1337)
    ds=TaskMivraRightsGatedDataset(args.manifest); dl=DataLoader(ds,batch_size=args.batch,shuffle=True,num_workers=0,drop_last=False)
    model=TaskMivraTargetSpeakerNet().to(args.device); opt=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=1e-4)
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    for epoch in range(1,args.epochs+1):
        model.train(); total=0.; started=time.time()
        for batch in dl:
            mix=batch['mixture'].to(args.device); target=batch['target'].to(args.device); profile=batch['profile'].to(args.device)
            est,mask=model(mix,profile)
            loss=si_sdr_loss(est,target)+2.0*spectral_loss(est,target)+0.01*(mask[:,:,1:]-mask[:,:,:-1]).abs().mean()
            opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),5.0); opt.step(); total+=float(loss.detach())
        meta={'epoch':epoch,'loss':total/max(1,len(dl)),'seconds':time.time()-started,'architecture':'TaskMivraTargetSpeakerNet-v1','pretrained_weights':False}
        print(json.dumps(meta))
        torch.save({'model':model.state_dict(),'meta':meta},out/f'taskmivra-target-speaker-epoch-{epoch:03d}.pt')
if __name__=='__main__': main()
