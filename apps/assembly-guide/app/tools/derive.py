"""Derive assembled poses for the Soyspray print-pack STLs from the RackStack SCAD transforms.

World frame (millimetres): x = left -> right, y = front -> rear, z = up.
Origin = front-left-bottom corner of the lower (new) frame's bottom yBar.
"""
import json, math, os, sys
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from stlinfo import load_stl

RACKSTACK = os.environ['RACKSTACK']
STL_DIR = f'{RACKSTACK}/print-pack/soyspray-prototype/stl'
FILES = {
    'yBarLeft': 'QTY-2_yBarLeft.stl',
    'yBarRight': 'QTY-2_yBarRight.stl',
    'xBar': 'QTY-4_xBar.stl',
    'mainRail': 'QTY-4_mainRail.stl',
    'xyPlate': 'QTY-2_xyPlate.stl',
    'rackFeet': 'QTY-2_rackFeet.stl',
    'rackJoiner': 'QTY-4_rackJoiner.stl',
    'trayVent': 'QTY-3_m920q-ventilated-tray.stl',
    'trayUpper': 'QTY-3_upper-equipment-tray.stl',
}

# ---------------------------------------------------------------- matrices
def T(x=0, y=0, z=0):
    m = np.eye(4); m[:3, 3] = [x, y, z]; return m

def S(x=1, y=1, z=1):
    return np.diag([x, y, z, 1.0])

def Rx(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    m = np.eye(4); m[1, 1] = c; m[1, 2] = -s; m[2, 1] = s; m[2, 2] = c; return m

def Ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    m = np.eye(4); m[0, 0] = c; m[0, 2] = s; m[2, 0] = -s; m[2, 2] = c; return m

def Rz(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    m = np.eye(4); m[0, 0] = c; m[0, 1] = -s; m[1, 0] = s; m[1, 1] = c; return m

def mirror(axis):
    return S(*[-1 if i == axis else 1 for i in range(3)])

inv = np.linalg.inv
EPS = 0.001  # RackStack's eps used in yBarXBarConnectorTrans

# RackStack mini-profile constants (cross-checked against transforms.echo.txt below)
yBarWidth, yBarDepth, yBarHeight = 26, 209, 15
railTotalHeight, railFootThickness = 176, 3
xBarX, xBarSideThickness = 201, 8
stackConnectorDx, connectorBottomToScrew = 233, 6
mainRailSlideHexOnYBarDx, mainRailSlideHexOnYBarDy = 7.5, 10
xyPlateConnDx, xyPlateConnDy = 213, 133

yBarMirrorOtherCornerTrans = T(0, yBarDepth, 0) @ mirror(1)
yBarMainRailConnectorTrans = T(yBarWidth - (12 + 2), 3, yBarHeight - railFootThickness)
yBarXBarConnectorTrans = T(yBarWidth + EPS, 0, 0)
yBarStackConnectorTrans = T(5, 5, 0)
yBarBasePlateConnectorTrans = T(yBarWidth - 12, 32, 0)
xBarYBarConnectorTrans = Rz(-90)
xBarMirrorOtherCornerTrans = T(0, xBarX, 0) @ mirror(1)
mirrorMainRailOtherSideTrans = T(0, 0, railTotalHeight) @ mirror(2)

# xBarConnectorToYBarConnectorTrans lives in xBarYBarConnectors.scad; take the exact matrices echoed by OpenSCAD.

def parse_echo(path):
    mats, vars_ = {}, {}
    for line in open(path):
        line = line.strip().strip('"')
        if line.startswith('MAT '):
            k, v = line[4:].split('=', 1)
            mats[k] = np.array(json.loads(v), dtype=float)
        elif line.startswith('VAR '):
            k, v = line[4:].split('=', 1)
            vars_[k] = v
    return mats, vars_

ECHO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'transforms.echo.txt')
M, V = parse_echo(ECHO)
assert int(V['yBarWidth']) == yBarWidth and int(V['yBarDepth']) == yBarDepth
assert int(V['railTotalHeight']) == railTotalHeight and int(V['xBarX']) == xBarX
assert float(V['mainRailSlideHexOnYBarDx']) == mainRailSlideHexOnYBarDx

xBarSpaceToYBarSpace = M['xBarSpaceToYBarSpace']
yBarSpaceToXBarSpace = M['yBarSpaceToXBarSpace']
mR = xBarSpaceToYBarSpace @ xBarMirrorOtherCornerTrans @ yBarSpaceToXBarSpace
upperXYTrayTrans = yBarMainRailConnectorTrans @ mirrorMainRailOtherSideTrans @ inv(yBarMainRailConnectorTrans)
secondStackTrans = upperXYTrayTrans @ mirror(2)
feetToYBarTrans0 = T(5, 5, 0) @ yBarStackConnectorTrans @ mirror(1)
stackConnectorTrans0 = upperXYTrayTrans @ yBarStackConnectorTrans
xyPlateToYBarTrans = T(6, 6, 0) @ yBarBasePlateConnectorTrans
mainRailPrint = np.array([[0, 0, -1, railTotalHeight], [0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)
feetPrint = Rx(90 - 40)

for name, mine in [('mR', mR), ('upperXYTrayTrans', upperXYTrayTrans), ('secondStackTrans', secondStackTrans),
                   ('feetToYBarTrans0', feetToYBarTrans0), ('stackConnectorTrans0', stackConnectorTrans0),
                   ('xyPlateToYBarTrans', xyPlateToYBarTrans), ('mainRailPrintOrientation', mainRailPrint),
                   ('feetPrint', feetPrint), ('yBarMirrorOtherCornerTrans', yBarMirrorOtherCornerTrans),
                   ('yBarMainRailConnectorTrans', yBarMainRailConnectorTrans)]:
    assert np.allclose(mine, M[name], atol=2e-5), (name, mine, M[name])

corners = [np.eye(4), yBarMirrorOtherCornerTrans,
           mR @ yBarMirrorOtherCornerTrans, mR]  # mirrorAllTrayCornersFromYBarSpace order: FL, RL, RR, FR

# ---------------------------------------------------------------- meshes
meshes = {}
for key, fn in FILES.items():
    tris = load_stl(f'{STL_DIR}/{fn}')
    meshes[key] = tris.reshape(-1, 3)

def bbox(v):
    return v.min(0), v.max(0)

def symmetries(key):
    """Reflections (about the bbox centre planes) that map the mesh onto itself.

    CGAL triangulates coplanar faces differently at mirrored ends, so a few vertices of a symmetric part
    have no mirrored twin. Accept a reflection when >= 97 % of vertices match within 0.02 mm, or when
    every vertex matches within 0.25 mm (RackStack's 0.2 mm plug slack is applied on one side only).
    """
    v = np.unique(np.round(meshes[key], 4), axis=0)
    lo, hi = bbox(v); c = (lo + hi) / 2
    tree = cKDTree(v)
    found = []
    for axis in range(3):
        m = T(*c) @ mirror(axis) @ T(*-c)
        mv = (m[:3, :3] @ v.T).T + m[:3, 3]
        d, _ = tree.query(mv)
        frac = float((d < 0.02).mean())
        if frac >= 0.97 or d.max() < 0.25:
            found.append((axis, m, frac))
    found.sort(key=lambda f: -f[2])
    return [(a, m) for a, m, _ in found]

SYM = {k: symmetries(k) for k in FILES}

def resolve(part, W):
    """Return (part, proper matrix) placing an STL so it occupies the same volume as W*STL."""
    if np.linalg.det(W[:3, :3]) > 0:
        return part, W
    if part in ('yBarLeft', 'yBarRight'):
        other = 'yBarRight' if part == 'yBarLeft' else 'yBarLeft'
        return other, W @ mirror(0)  # yBarRight STL = mirror([1,0,0]) yBarLeft STL
    for axis, m in SYM[part]:
        Wp = W @ m
        assert np.linalg.det(Wp[:3, :3]) > 0
        return part, Wp
    raise RuntimeError(f'{part} has no mirror symmetry to resolve improper placement')

# Print orientation P: STL = P * canonical  ->  canonical = P^-1 * STL
P = {
    'yBarLeft': np.eye(4), 'yBarRight': mirror(0), 'xBar': np.eye(4), 'mainRail': mainRailPrint,
    'xyPlate': np.eye(4), 'rackFeet': feetPrint, 'rackJoiner': np.eye(4),
    'trayVent': np.eye(4), 'trayUpper': np.eye(4),
}

def place(part, A):
    """A: assembly transform of the canonical part (yBar() etc.). Returns resolved (part, W)."""
    canon_part = 'yBarLeft' if part == 'yBar' else part
    W = A @ inv(P[canon_part])
    return resolve(canon_part, W)

# ---------------------------------------------------------------- instances (local to their group)
inst = []  # dicts: id, group, part, W (4x4, maps STL coords -> group-local mm)

def add(iid, group, part, A):
    p, W = place(part, A)
    inst.append({'id': iid, 'group': group, 'part': p, 'W': W})

def rectangle(prefix, group):
    add(f'{prefix}.yL', group, 'yBar', np.eye(4))
    add(f'{prefix}.yR', group, 'yBar', mR)
    add(f'{prefix}.xF', group, 'xBar', xBarSpaceToYBarSpace)
    add(f'{prefix}.xR', group, 'xBar', yBarMirrorOtherCornerTrans @ xBarSpaceToYBarSpace)

rail_frames = {
    'FL': yBarMainRailConnectorTrans,
    'RL': yBarMirrorOtherCornerTrans @ yBarMainRailConnectorTrans,
    'FR': mR @ yBarMainRailConnectorTrans,
    'RR': mR @ yBarMirrorOtherCornerTrans @ yBarMainRailConnectorTrans,
}

# Top rectangle is built exactly like the bottom one, then turned over about the front-rear axis.
# flipTrans maps the bottom rectangle onto RackStack's upperXYTrayTrans placement with a proper rotation.
flipTrans = T(253 + 2 * EPS, 0, 200) @ Ry(180)

def frame(prefix):
    """One complete RackStack frame: two rectangles, four rails, two xyPlates (group-local)."""
    rectangle(f'{prefix}.rectB', f'{prefix}')
    for k, A in rail_frames.items():
        add(f'{prefix}.rail{k}', f'{prefix}', 'mainRail', A)
    rectangle(f'{prefix}.rectT', f'{prefix}.rectT')  # local to the flipping group
    add(f'{prefix}.plateB', f'{prefix}', 'xyPlate', xyPlateToYBarTrans)
    add(f'{prefix}.plateT', f'{prefix}', 'xyPlate', upperXYTrayTrans @ xyPlateToYBarTrans)

frame('new')
frame('old')
add('foot.F', 'world', 'rackFeet', feetToYBarTrans0)
add('foot.R', 'world', 'rackFeet', yBarMirrorOtherCornerTrans @ feetToYBarTrans0)
for i, C in enumerate(corners):
    add(f'joiner.{["FL", "RL", "RR", "FR"][i]}', 'world', 'rackJoiner',
        C @ stackConnectorTrans0 @ T(0, 10, 0) @ mirror(1))

# Trays: ear holes (tray STL coords) at x = -15 / 200, z = 1.5 and 1.5 + 10u; ear back face y = 0.
# Rail holes (world) at x = 19 / 234.002, z = bay + 25 + 10(k-1); rail front face y = 3.
TRAY_X, TRAY_Y = 34.0, 3.0
def hole_z(bay, k):
    return bay * 200 + 25 + 10 * (k - 1)
LOWER_HOLES = [1, 6, 11]
UPPER_HOLES = [1, 5, 10]
for i, k in enumerate(LOWER_HOLES):
    add(f'tray.L{i}', 'world', 'trayVent', T(TRAY_X, TRAY_Y, hole_z(0, k) - 1.5))
for i, k in enumerate(UPPER_HOLES):
    add(f'tray.U{i}', 'world', 'trayUpper', T(TRAY_X, TRAY_Y, hole_z(1, k) - 1.5))

# ---------------------------------------------------------------- screws (head = top of the countersunk head)
screws = []  # id, group, type, head (group-local), dir (unit shaft direction), out (exploded distance)

def add_screw(sid, group, kind, M, out):
    """M: RackStack screw frame; head at origin, shaft along -z (counterSunkHead_N)."""
    head = M[:3, 3]
    d = -M[:3, 2]; d = d / np.linalg.norm(d)
    screws.append({'id': sid, 'group': group, 'type': kind, 'head': head, 'dir': d, 'out': out})

xBarYBarScrewTrans0 = T(27, xBarSideThickness, 8) @ Rx(270)
railScrewLocal = T(mainRailSlideHexOnYBarDx, mainRailSlideHexOnYBarDy, -5) @ Rx(-45) @ T(0, 0, 14)
feetScrewLocal = T(-9, 0, connectorBottomToScrew) @ Ry(-90)
mirrorOtherFeetStackConnectorTrans = T(stackConnectorDx, 0, 0) @ mirror(0)
assert np.allclose(railScrewLocal, M['railScrewLocal'], atol=2e-5)
assert np.allclose(feetScrewLocal, M['feetScrewLocal'], atol=2e-5)
assert np.allclose(xBarYBarScrewTrans0, M['xBarYBarScrewTrans'], atol=2e-5)

def rectangle_screws(prefix, group):
    for bar, A in [('F', xBarSpaceToYBarSpace), ('R', yBarMirrorOtherCornerTrans @ xBarSpaceToYBarSpace)]:
        add_screw(f'{prefix}.s{bar}L', group, 'm3x16', A @ xBarYBarScrewTrans0, 16)
        add_screw(f'{prefix}.s{bar}R', group, 'm3x16', A @ xBarMirrorOtherCornerTrans @ xBarYBarScrewTrans0, 16)

def frame_screws(prefix):
    rectangle_screws(f'{prefix}.rectB', prefix)
    rectangle_screws(f'{prefix}.rectT', f'{prefix}.rectT')
    for k, F in rail_frames.items():
        add_screw(f'{prefix}.rail{k}.sB', prefix, 'm3x16', F @ railScrewLocal, 16)
    for k, C in zip(['FL', 'RL', 'RR', 'FR'], corners):
        add_screw(f'{prefix}.rail{k}.sT', prefix, 'm3x16',
                  upperXYTrayTrans @ C @ yBarMainRailConnectorTrans @ railScrewLocal, 16)
    for plate, F in [('B', np.eye(4)), ('T', upperXYTrayTrans)]:
        for i, (dx, dy) in enumerate([(0, 0), (xyPlateConnDx, 0), (0, xyPlateConnDy), (xyPlateConnDx, xyPlateConnDy)]):
            add_screw(f'{prefix}.plate{plate}.s{i}', prefix, 'm3x12', F @ xyPlateToYBarTrans @ T(dx, dy, 0) @ mirror(2), 20)

frame_screws('new')
frame_screws('old')
for foot, F in [('F', feetToYBarTrans0), ('R', yBarMirrorOtherCornerTrans @ feetToYBarTrans0)]:
    add_screw(f'foot.{foot}.sL', 'world', 'm3x12', F @ feetScrewLocal, 20)
    add_screw(f'foot.{foot}.sR', 'world', 'm3x12', F @ mirrorOtherFeetStackConnectorTrans @ feetScrewLocal, 20)
for level, F in [('lo', upperXYTrayTrans), ('up', secondStackTrans)]:
    for k, C in zip(['FL', 'RL', 'RR', 'FR'], corners):
        add_screw(f'joiner.{k}.s{level}', 'world', 'm3x12', F @ C @ feetToYBarTrans0 @ feetScrewLocal, 15)

def tray_screws(tid, z_low, u):
    for side, x in [('L', 19.0), ('R', 253 + 2 * EPS - 19.0)]:
        for lvl, z in [('lo', z_low), ('hi', z_low + 10 * u)]:
            Mh = T(x, 0, z) @ Rx(90)  # head on the ear face (y = 0), shaft into the rail (+y)
            add_screw(f'{tid}.s{side}{lvl}', 'world', 'm4x12', Mh, 24)
for i, k in enumerate(LOWER_HOLES):
    tray_screws(f'tray.L{i}', hole_z(0, k), 4)
for i, k in enumerate(UPPER_HOLES):
    tray_screws(f'tray.U{i}', hole_z(1, k), 3)

# ---------------------------------------------------------------- world matrices for checks
GROUP_FINAL = {
    'world': np.eye(4),
    'new': np.eye(4),
    'new.rectT': flipTrans,
    'old': secondStackTrans,
    'old.rectT': secondStackTrans @ flipTrans,
}

def world(W, group):
    return GROUP_FINAL[group] @ W

def world_bbox(part, Wm):
    v = meshes[part]
    wv = (Wm[:3, :3] @ v.T).T + Wm[:3, 3]
    return wv.min(0), wv.max(0)

report = {}
for it in inst:
    Wm = world(it['W'], it['group'])
    lo, hi = world_bbox(it['part'], Wm)
    report[it['id']] = (it['part'], np.round(lo, 2), np.round(hi, 2))

# Cross-check rectT against RackStack's own (improper) upperXYTrayTrans placement: same occupied volume.
def same_volume(partA, WA, partB, WB):
    va = (WA[:3, :3] @ meshes[partA].T).T + WA[:3, 3]
    vb = (WB[:3, :3] @ meshes[partB].T).T + WB[:3, 3]
    ta = cKDTree(np.unique(np.round(vb, 3), axis=0))
    d, _ = ta.query(np.unique(np.round(va, 3), axis=0))
    return float(np.percentile(d, 99))  # CGAL leaves a few unmatched triangulation vertices

checks = []
def check(name, ok, detail=''):
    checks.append((name, bool(ok), detail))

# Turning the rectangle over about the front-rear axis moves the bottom-left yBarLeft to the top-right corner.
for side, A in [('yL', mR), ('yR', np.eye(4)), ('xF', xBarSpaceToYBarSpace),
                ('xR', yBarMirrorOtherCornerTrans @ xBarSpaceToYBarSpace)]:
    it = next(i for i in inst if i['id'] == f'new.rectT.{side}')
    canon = 'xBar' if side.startswith('x') else 'yBarLeft'
    ref_W = upperXYTrayTrans @ A @ inv(P[canon])  # improper reference, same volume
    d = same_volume(it['part'], world(it['W'], it['group']), canon, ref_W)
    check(f'top rectangle {side} matches upperXYTrayTrans volume', d < 0.01, f'max dev {d:.4f} mm, part {it["part"]}')

def bb(iid):
    return report[iid][1], report[iid][2]

lo, hi = bb('new.railFL'); check('rail spans z 12..188', abs(lo[2] - 12) < 0.01 and abs(hi[2] - 188) < 0.01, f'{lo} {hi}')
lo, hi = bb('new.rectT.xF'); check('top xBar spans z 185..200', abs(lo[2] - 185) < 0.01 and abs(hi[2] - 200) < 0.01, f'{lo} {hi}')
lo, hi = bb('new.plateT'); check('top plate spans z 195..200', abs(lo[2] - 195) < 0.01 and abs(hi[2] - 200) < 0.01, f'{lo} {hi}')
lo, hi = bb('old.rectB.xF'); check('2024 frame bottom xBar at z 200..215', abs(lo[2] - 200) < 0.01, f'{lo} {hi}')
lo, hi = bb('joiner.FL'); check('joiner straddles z=200', abs((lo[2] + hi[2]) / 2 - 200) < 0.01, f'{lo} {hi}')
lo, hi = bb('foot.F'); check('front foot plugs 10.5 mm into the bottom sockets', abs(hi[2] - 10.5) < 0.05 and lo[2] < 0, f'{lo} {hi}')
lo, hi = bb('new.rectB.yR'); check('right yBar at x 223..253', abs(hi[0] - 252.906) < 0.01, f'{lo} {hi}')

# Tray ear holes vs rail holes: find the hole circle centres on the ear front plate.
def ear_hole_centres(part):
    v = np.unique(np.round(meshes[part], 4), axis=0)
    out = []
    for cx in (-15.0, 200.0):
        for cz in (1.5, 31.5, 41.5):
            sel = v[(np.abs(v[:, 1] + 3) < 1e-3) & (np.hypot(v[:, 0] - cx, v[:, 2] - cz) < 3.0)]
            if len(sel) >= 6:
                r = np.hypot(sel[:, 0] - cx, sel[:, 2] - cz)
                out.append((cx, cz, len(sel), round(float(r.mean()), 3), round(float(r.std()), 4)))
    return out
check('vent tray ear holes at x -15/200, z 1.5/41.5', len(ear_hole_centres('trayVent')) == 4, str(ear_hole_centres('trayVent')))
check('upper tray ear holes at x -15/200, z 1.5/31.5', len(ear_hole_centres('trayUpper')) == 4, str(ear_hole_centres('trayUpper')))

# Rail M4 holes on the front face: canonical x = 7, z = 13 + 10k -> STL X = 176 - z, Z = 7, front face Y = 0
def rail_holes():
    v = np.unique(np.round(meshes['mainRail'], 4), axis=0)
    hits = 0
    for k in range(16):
        X = 176 - (13 + 10 * k)
        sel = v[(np.abs(v[:, 1]) < 1e-3) & (np.hypot(v[:, 0] - X, v[:, 2] - 7) < 2.6)]
        if len(sel) >= 6:
            hits += 1
    return hits
check('mainRail has 16 front holes on the 10 mm pitch', rail_holes() == 16, f'{rail_holes()} found')

def sw(sid):
    sc = next(x for x in screws if x['id'] == sid)
    return world(np.r_[sc['head'], 1.0][:, None].repeat(1, 1) if False else T(*sc['head']), sc['group'])[:3, 3], sc['dir']
h, d = sw('new.rectB.sFL'); check('corner screw heads sit inside the xBar channel', 0 <= h[2] <= 15, f'{np.round(h, 2)} dir {np.round(d, 3)}')
h, d = sw('new.railFL.sB'); check('bottom rail screw at 45 degrees into the yBar', abs(abs(d[2]) - 0.7071) < 1e-3 and h[2] < 30, f'{np.round(h, 2)} dir {np.round(d, 3)}')
h, d = sw('new.railFL.sT'); check('top rail screw mirrored near z=200', h[2] > 170 and d[2] > 0, f'{np.round(h, 2)} dir {np.round(d, 3)}')
h, d = sw('foot.F.sL'); check('front foot screw enters from the left face', abs(h[0] - 1) < 1e-6 and d[0] > 0.99, f'{np.round(h, 2)} dir {np.round(d, 3)}')
h, d = sw('joiner.FL.slo'); check('joiner screw in lower frame at z 194', abs(h[2] - 194) < 1e-6, f'{np.round(h, 2)} dir {np.round(d, 3)}')
h, d = sw('joiner.FL.sup'); check('joiner screw in upper frame at z 206', abs(h[2] - 206) < 1e-6, f'{np.round(h, 2)} dir {np.round(d, 3)}')
h, d = sw('new.plateB.s0'); check('bottom plate screw points up from z 0', abs(h[2]) < 1e-6 and d[2] > 0.99, f'{np.round(h, 2)} dir {np.round(d, 3)}')
h, d = sw('tray.L0.sLlo'); check('tray screw on rail hole 1 at z 25', abs(h[2] - 25) < 1e-6 and d[1] > 0.99, f'{np.round(h, 2)} dir {np.round(d, 3)}')
print('screws:', len(screws))

for name, ok, detail in checks:
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail else ''))
print()
print('symmetries:', {k: [a for a, _ in v] for k, v in SYM.items()})
for k, (p, lo, hi) in report.items():
    print(f'{k:16s} {p:11s} {lo} {hi}')

def quat(R):
    tr = np.trace(R)
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2; w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s; y = (R[0, 2] - R[2, 0]) / s; z = (R[1, 0] - R[0, 1]) / s
    else:
        i = int(np.argmax(np.diag(R)))
        if i == 0:
            s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
            w = (R[2, 1] - R[1, 2]) / s; x = 0.25 * s; y = (R[0, 1] + R[1, 0]) / s; z = (R[0, 2] + R[2, 0]) / s
        elif i == 1:
            s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
            w = (R[0, 2] - R[2, 0]) / s; x = (R[0, 1] + R[1, 0]) / s; y = 0.25 * s; z = (R[1, 2] + R[2, 1]) / s
        else:
            s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
            w = (R[1, 0] - R[0, 1]) / s; x = (R[0, 2] + R[2, 0]) / s; y = (R[1, 2] + R[2, 1]) / s; z = 0.25 * s
    q = np.array([x, y, z, w]); q /= np.linalg.norm(q)
    if q[3] < 0: q = -q
    return [round(float(a), 7) for a in q]

def rnd(v, n=4):
    return [round(float(a), n) for a in v]

def pose_of(W, centre):
    Wc = W @ T(*centre)
    R = Wc[:3, :3]
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-6) and np.linalg.det(R) > 0.999
    return rnd(Wc[:3, 3]), quat(R)

if '--json' in sys.argv:
    out = sys.argv[sys.argv.index('--json') + 1]
    centres = {k: (bbox(meshes[k])[0] + bbox(meshes[k])[1]) / 2 for k in FILES}
    rect_pivot = np.array([(253 + 2 * EPS) / 2, yBarDepth / 2, 7.5])
    frame_pivot = np.array([(253 + 2 * EPS) / 2, yBarDepth / 2, 100.0])
    def group(parent, pivot, final_W):
        p, q = pose_of(final_W, pivot)
        return {'parent': parent, 'pivot': rnd(pivot), 'p': p, 'q': q}
    data = {
        'frame': 'mm; x left->right, y front->rear, z up; origin = front-left-bottom of the lower frame',
        'trayHoles': {'lower': LOWER_HOLES, 'upper': UPPER_HOLES},
        'parts': {k: {'centre': rnd(c)} for k, c in centres.items()},
        'groups': {
            'new': group('world', frame_pivot, np.eye(4)),
            'new.rectT': group('new', rect_pivot, flipTrans),
            'old': group('world', frame_pivot, secondStackTrans),
            'old.rectT': group('old', rect_pivot, flipTrans),
        },
        'instances': [],
    }
    for it in inst:
        p, q = pose_of(it['W'], centres[it['part']])
        lo, hi = world_bbox(it['part'], world(it['W'], it['group']))
        data['instances'].append({'id': it['id'], 'group': it['group'], 'part': it['part'], 'p': p, 'q': q,
                                  'worldMin': rnd(lo, 2), 'worldMax': rnd(hi, 2)})
    data['screws'] = [{'id': sc['id'], 'group': sc['group'], 'type': sc['type'], 'head': rnd(sc['head']),
                       'dir': rnd(sc['dir'], 6), 'out': sc['out']} for sc in screws]
    json.dump(data, open(out, 'w'), indent=1)
    print('wrote', out)

if not all(ok for _, ok, _ in checks):
    sys.exit(1)
