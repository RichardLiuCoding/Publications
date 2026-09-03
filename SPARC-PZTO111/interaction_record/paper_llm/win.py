import re,sys
txt=open('<DRIVE>/Coding/Trajectory Lithography/TrajectoryLitho/chat_history_260814.md',encoding='utf-8').read()
pat=re.compile(r'^## (\d+)\. (User|Claude)\s+·\s+(\S+ \S+)$', re.M)
H=[(int(m.group(1)),m.group(2),m.group(3),m.start()) for m in pat.finditer(txt)]
pos={h[0]:h for h in H}; starts=sorted(h[3] for h in H)
def body(n,cap=1400):
    s=pos[n][3]; nxt=min([x for x in starts if x>s]+[len(txt)])
    return ' '.join(txt[s:nxt].split())[:cap]
a,b=int(sys.argv[1]),int(sys.argv[2]); cap=int(sys.argv[3]) if len(sys.argv)>3 else 1400
for n in range(a,b+1):
    if n in pos: print(f"\n=== {n}. {pos[n][1]} {pos[n][2]} ===\n{body(n,cap)}")
