"""Evidence-only: XTEST input on the job's private Xvfb server. status adds two read-only observations."""
from pathlib import Path
import os, subprocess as sp, json, time, sys, tempfile
mode = sys.argv[1]
bin = str(Path('target/debug/herdr-app').resolve())
scratch = Path(tempfile.mkdtemp(prefix='h1489-'))
home = scratch/'home'; (home/'layouts').mkdir(parents=True)
env = {**os.environ,'HERDR_APP_HOME':str(home),'HC_SESSION':'divider-'+mode,'XDG_STATE_HOME':str(scratch/'state'),'HERDR_APP_NO_SOUND':'1'}
def run(*args): return sp.check_output(args, env=env, text=True, timeout=10).strip()
def cmd(*args):
    v = json.loads(run(bin,*args)); assert not (isinstance(v,dict) and v.get('error')), v; return v
def do(c, **args): return cmd('do',c,json.dumps(args))
def until(f):
    end=time.monotonic()+18; value=None
    while time.monotonic()<end:
        if app.poll() is not None: raise RuntimeError('app exited')
        try:
            value=f()
            if value: return value
        except (sp.SubprocessError, ValueError): pass
        time.sleep(.12)
    raise RuntimeError(f'not ready: {value}')
layout={'id':'probe-root','type':'row','titlebar':'none','divider':{'width':1,'color':'border'},'children':[{'id':'probe-left','type':'column','size':{'px':170},'children':[]},{'id':'work','type':'block','content':{'tab':'active'}}]}
for file,val in [('layouts/probe',layout),('shared',{'frame.welcomed':'skipped','layout':'probe'}),('settings',{'zoom':1,'telemetry':False}),('update-notes',{'last_run':'0.1.18','presented':['0.1.18']})]: (home/(file+'.json')).write_text(json.dumps(val))
log=(scratch/'app.log').open('w'); app=sp.Popen([bin],env=env,stdout=log,stderr=log)
try:
    until(lambda: (home/'herdr-app.sock').exists() and cmd('status').get('probe_edge'))
    do('space.new',name='Probe',folder='/tmp',argv=['/bin/sh','-c',"for i in $(seq 1 60); do printf 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\\r\\n'; done; exec sleep 600"])
    until(lambda: cmd('status')['probe_terms']); time.sleep(1)
    win=until(lambda: run('xdotool','search','--onlyvisible','--pid',str(app.pid)).splitlines()[-1:])[0]
    run('xdotool','windowactivate','--sync',win)
    rows=[]
    for offset in (20,0,2,3,4):
        do('layout.resize',id='probe-left',px=170); until(lambda: cmd('status')['probe_edge']==170)
        do('terminal.clear_selection'); until(lambda: not any(t['selection'] for t in cmd('status')['probe_terms'].values()))
        x=170+offset; y=115
        run('xdotool','mousemove','--window',win,str(x),str(y),'mousedown','1','sleep','0.05','mousemove','--window',win,str(x+80),str(y),'sleep','0.07','mouseup','1'); time.sleep(.35)
        s=cmd('status'); row=(offset,s['probe_edge'],any(t['selection'] for t in s['probe_terms'].values())); rows.append(row); print(mode,row,flush=True)
    assert rows[0][1:]==(170,True) and rows[-1][1:]==(170,True) and rows[1][1]!=170 and not rows[1][2], rows
    inside=[r for r in rows if r[0] in (2,3)]; assert all(r[1]!=170 for r in inside), rows
    if mode=='before': assert any(r[2] for r in inside), 'no X11 baseline reproduction'
    else: assert not any(r[2] for r in inside), 'overlap still selects'
finally:
    app.terminate()
    try: app.wait(5)
    except sp.TimeoutExpired: app.kill(); app.wait()
    sp.run(['hc','server','stop'],env=env,timeout=12,check=False); log.close()
    print((scratch/'app.log').read_text(errors='replace')[-2500:])
