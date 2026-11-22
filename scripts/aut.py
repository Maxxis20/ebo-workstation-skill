#!/usr/bin/env python3
"""aut.py - write an EBO / Menta Function Block program text file (.aut) from a description in Python.

    from aut import Program
    p = Program("Blink")
    osc = p.block("OSC", "Blink", params=[4, 2])
    out = p.block("BO", "BlinkOut")
    p.wire(osc, out)
    p.save("blink.aut")

Format facts are in ../reference/findings.md. Block names, pin counts and parameter counts are checked
against the editor's own catalogue (reference/MentaBlocks.xml) where the block is listed there.
"""
import math, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE = os.path.join(HERE, "..", "reference", "MentaBlocks.xml")

# flag = last number in [x,y,0,flag]. Seen in the shipped macro library: bit 0 = public.
# Parameter blocks carry 6 when private and 7 when public; SR carries 4 when private.
BASE_FLAG = {"PVR": 6, "PVB": 6, "PVI": 6, "SR": 4}
# Pin numbers in the file are not always the order drawn on the block. PIDA: taken from the shipped macro
# Heating/Control/HOTWATER.AUT (gain on 4, integral time on 5, tracking signal on 3) and its wire end points.
PINS = {"PIDA": {"MV": 0, "SP": 1, "Mode": 2, "TSg": 3, "G": 4, "Ti": 5, "Td": 6, "DZ": 7},
        "SR": {"s": 0, "r": 1}}
SLOT = {"PIDA": {0: 0, 1: 1, 2: 2, 3: 7, 4: 3, 5: 4, 6: 5, 7: 6}}   # pin number -> position on the block, from the top
EXPR = {"XPR", "XPB", "XPI"}                      # one parameter in braces, inputs = letters used
OPERATOR = re.compile(r"^Op")                     # operator blocks (OpR, OpW, Op?:, Op- ...): not in the catalogue


class Block:
    def __init__(self, prog, typ, name, params, unit, desc, public, module, n_in):
        self.prog, self.typ, self.name, self.params = prog, typ, name, params
        self.unit, self.desc, self.public, self.module = unit, desc, public, module
        self.n_in = n_in
        self.id = None; self.x = self.y = 0

    @property
    def full_name(self):
        return f"{self.module}\\{self.name}" if self.module and self.name else self.name

    # Geometry in grid cells, measured off the editor with a calibration sheet (reference/findings.md).
    TWO_PARAM = {"DELAY", "LIMIT", "HYST", "OSC", "CURVE"}        # 10 wide, 14 high, pin and output at 7
    SATELLITE = {"OpR", "OpW", "OpB"}                              # constant operators: 9 x 3, output at the top

    def size(self):
        t = self.typ
        if t in EXPR:
            n = self.n_in
            return max(10, math.ceil(1.5 * len(str(self.params[0])) + 2.5)), (10 if n <= 3 else 3 * n - 1)
        if t in ("RI", "BI", "II"):
            return 18, (10 if t == "RI" else 6)                    # 8 cells of input stub, then the body
        if t in ("RO", "BO", "IO"):
            return 16, 6                                           # body 10, then the output stub
        if t == "PIDA":
            return 15, 27
        if t == "SR":
            return 12, 10
        if t in self.TWO_PARAM:
            return 10, 14
        if t in self.SATELLITE:
            return 9, 3
        if t in ("AND", "OR", "XOR"):
            return 6, 6
        return 10, 10

    def out_xy(self):
        w, h = self.size()
        return self.x + w, self.y + (h + 1) // 2

    def in_xy(self, pin):
        w, h = self.size()
        n = max(1, self.n_in)
        if self.typ == "PIDA":
            dy = 3 + 3 * SLOT["PIDA"][pin]
        elif self.typ in ("AND", "OR", "XOR"):
            dy = 1 + 4 * pin
        elif n == 1:
            dy = (h + 1) // 2
        elif n == 2:
            dy = (2, 8)[pin]
        elif n == 3:
            dy = (1, 5, 9)[pin]
        else:
            dy = 1 + 3 * pin
        return self.x, self.y + dy

    def line(self):
        flag = BASE_FLAG.get(self.typ, 0) | (1 if self.public else 0)
        if self.typ in EXPR:
            par = "{" + str(self.params[0]) + "}"
        elif self.typ == "CURVE":
            lim, pts = self.params[0], self.params[1:]
            pairs = [f"{fmt(pts[i])},{fmt(pts[i + 1])}" for i in range(0, len(pts), 2)]
            par = "(" + fmt(lim) + "," + ", ".join(pairs) + ")"
        elif self.typ == "COMENT":
            return f'#{self.id} "" [{self.x},{self.y},0,0] \'\',\'\' = COMENT {{Arial,-13,700,0,0,0,0,0,0 :{self.params[0]}}},5'
        else:
            par = "(" + ",".join(fmt(v) for v in self.params) + ")"
        return f'#{self.id} "{self.full_name}" [{self.x},{self.y},0,{flag}] \'{self.unit}\',\'{self.desc}\' = {self.typ} {par}'


def fmt(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return repr(v) if v != int(v) else str(int(v))
    return str(v)


def expr_inputs(expr):
    """Input letters of an expression, in pin order.

    The editor sorts them alphabetically. Whether capitals sort before lower case is not known, so
    an expression is refused unless both orders give the same pins: use early capitals for analog
    inputs and later lower-case letters for binary ones. Names of constants (two letters or more)
    are not inputs."""
    letters = sorted(set(re.findall(r"(?<![A-Za-z0-9_])([A-Za-z])(?![A-Za-z0-9_])", expr)))
    if len({c.lower() for c in letters}) != len(letters):
        raise ValueError(f"expression {expr!r} uses one letter in both cases")
    if letters != sorted(letters, key=str.lower):
        raise ValueError(f"expression {expr!r}: pin order ambiguous, keep capitals alphabetically before lower case")
    return letters


class Program:
    def __init__(self, title="", cycle_ms=1000):
        self.title, self.cycle_ms = title, cycle_ms
        self.blocks, self.wires, self.consts = [], [], []
        self.cat = {}
        if os.path.exists(CATALOGUE):
            for b in ET.parse(CATALOGUE).getroot().iter("block"):
                self.cat[b.get("name")] = (len(b.findall(".//input")),
                                           b.find("inputs").get("type") if b.find("inputs") is not None else "static",
                                           len(b.findall(".//parameter")))

    # --- content -----------------------------------------------------------------------------------
    def block(self, typ, name="", params=(), unit="", desc="", public=False, module="", inputs=None):
        params = list(params)
        if typ in EXPR:
            n_in = len(expr_inputs(str(params[0])))
        elif inputs is not None:
            n_in = inputs
        elif typ in self.cat:
            n_in = self.cat[typ][0]
        else:
            n_in = 0
        if typ in self.cat and typ not in EXPR and typ != "CURVE":
            want = self.cat[typ][2]
            if len(params) != want:
                raise ValueError(f"{typ} {name!r}: {len(params)} parameters given, catalogue lists {want}")
        elif typ not in self.cat and not OPERATOR.match(typ) and typ != "COMENT":
            raise ValueError(f"{typ}: not in the block catalogue")
        if name and any(b.full_name == (f"{module}\\{name}" if module else name) for b in self.blocks):
            raise ValueError(f"duplicate block name {name!r}")
        b = Block(self, typ, name, params, unit, desc, public, module, n_in)
        self.blocks.append(b)
        return b

    def const(self, name, value, unit=""):
        """Named constant, usable as a block parameter (DELAY, FILT, CURVE, LIMIT ...)."""
        self.consts.append((name, value, unit))
        return name

    def wire(self, src, dst, pin=0):
        if isinstance(pin, str) and dst.typ in PINS:            # named pin
            pin = PINS[dst.typ][pin]
        elif isinstance(pin, str):                              # letter of an expression block
            pin = expr_inputs(str(dst.params[0])).index(pin)
        if dst.n_in and pin >= dst.n_in and self.cat.get(dst.typ, (0, "static"))[1] == "static":
            raise ValueError(f"{dst.typ} {dst.name!r} has no input {pin}")
        if any(w[1] is dst and w[2] == pin for w in self.wires):
            raise ValueError(f"{dst.typ} {dst.name!r} input {pin} wired twice")
        self.wires.append((src, dst, pin))

    # --- layout and routing -------------------------------------------------------------------------
    def layout(self, x0=8, y0=4, gap_y=6, band_gap=8, pitch=2):
        """Lay out and route; when wires still share a row (a ring of outputs and foreign pins that no track order
        can untangle), push the source block of one of them a row down and try again."""
        self._nudge = {}
        for _ in range(40):
            self._layout(x0, y0, gap_y, band_gap, pitch)
            bad = self.overlaps()
            if not bad:
                return
            b = next(b for b in self.blocks if (b.full_name or "?") == bad[0][0] and id(b) in self.routes)
            self._nudge[id(b)] = self._nudge.get(id(b), 0) + 1

    def _layout(self, x0, y0, gap_y, band_gap, pitch):
        """Columns by signal depth, shared by all modules; one band per module; wires in free channels.

        Between two columns is a vertical channel, clear of blocks from top to bottom of the sheet, with
        one track per net. A wire to the next column of the same band goes out to its track, along it and
        into the pin. Any other wire climbs its track to a lane above the destination band, runs along
        the lane to a track in the channel left of the destination column and drops to the pin. So no
        wire crosses a block. Set values sit one column before the first block that reads them, and
        constant operators sit directly left of the pin they feed."""
        B = [b for b in self.blocks if b.typ != "COMENT"]
        order = {id(b): i for i, b in enumerate(B)}
        sat = {id(b) for b in B if b.typ in Block.SATELLITE}
        fwd = [(s, d, p) for s, d, p in self.wires if order[id(s)] < order[id(d)]]
        depth = {id(b): 0 for b in B}
        for _ in range(len(B)):
            ch = False
            for s, d, _p in fwd:
                if id(s) in sat:
                    continue
                if depth[id(d)] < depth[id(s)] + 1:
                    depth[id(d)] = depth[id(s)] + 1; ch = True
            if not ch:
                break
        has_in = {id(d) for _s, d, _p in self.wires}
        for b in B:                                             # sources as late as possible
            if id(b) not in has_in and b.typ not in ("RI", "BI", "II") and id(b) not in sat:
                use = [depth[id(d)] for s, d, _p in self.wires if s is b]
                if use:
                    depth[id(b)] = max(0, min(use) - 1)
        modules = []
        for b in B:
            if b.module not in modules:
                modules.append(b.module)
        ncol = max(depth.values()) + 1
        col = lambda b: depth[id(b)]
        # nets: source -> destinations; classify each destination as adjacent or by lane
        nets = {}
        for s, d, p in self.wires:
            if id(s) in sat:
                continue
            nets.setdefault(id(s), (s, []))[1].append((d, p))
        adjacent = lambda s, d: col(d) == col(s) + 1 and d.module == s.module
        tracks = [dict() for _ in range(ncol + 1)]              # tracks[c + 1] = channel right of column c
        lanes = {m: dict() for m in modules}
        for sid, (s, dst) in nets.items():
            tracks[col(s) + 1].setdefault(sid, len(tracks[col(s) + 1]))
            for d, _p in dst:
                if not adjacent(s, d):
                    tracks[col(d)].setdefault(sid, len(tracks[col(d)]))
                    lanes[d.module].setdefault(sid, len(lanes[d.module]))
        feeds_sat = [False] * (ncol + 1)                        # channel left of column c holds satellites
        for s, d, _p in self.wires:
            if id(s) in sat:
                feeds_sat[col(d)] = True
        colw = [max([b.size()[0] for b in B if col(b) == c and id(b) not in sat] or [10]) for c in range(ncol)]
        chan_x, X, x = [], [], x0
        for c in range(ncol):
            chan_x.append(x + 2)                                # first track of the channel left of column c
            x += 3 + pitch * len(tracks[c]) + (12 if feeds_sat[c] else 0) + (2 if tracks[c] else 0)
            X.append(x); x += colw[c]
        chan_x.append(x + 2)
        y = y0; lane_y = {}
        for m in modules:
            if m:
                self._title(m, x0, y); y += 5
            lane_y[m] = y
            y += pitch * len(lanes[m]) + 4
            bottom = y
            for c in range(ncol):
                yy = y
                for b in B:
                    if b.module == m and col(b) == c and id(b) not in sat:
                        yy += self._nudge.get(id(b), 0)
                        b.x, b.y = X[c], yy; yy += b.size()[1] + gap_y
                bottom = max(bottom, yy)
            y = bottom + band_gap
        for s, d, p in self.wires:
            if id(s) in sat:
                ix, iy = d.in_xy(p); s.x, s.y = ix - 11, iy - 1
        # Track order inside each channel. A wire leaving a block runs right to its track; a wire entering a pin
        # comes from its track on the left. When an output and a foreign pin sit on the same row, the two pieces
        # share that row, and they lie on top of each other unless the leaving net has the track further left.
        for ch in range(ncol + 1):
            out_row, in_rows = {}, {}
            for sid, (s, dst) in nets.items():
                if sid not in tracks[ch]:
                    continue
                if col(s) == ch - 1:
                    out_row[sid] = s.out_xy()[1]
                in_rows[sid] = {d.in_xy(p)[1] for d, p in dst if col(d) == ch}
            before = {n: {m for m in tracks[ch] if m != n and n in out_row and out_row[n] in in_rows[m]} for n in tracks[ch]}
            todo, done = sorted(tracks[ch], key=tracks[ch].get), []
            while todo:                                         # leftmost first: a net nobody still has to precede
                free = [n for n in todo if not any(n in before[m] for m in todo if m != n)]
                n = free[0] if free else todo[0]                # a ring of such pairs cannot be untangled by order
                todo.remove(n); done.append(n)
            tracks[ch] = {n: i for i, n in enumerate(done)}
        # routes
        self.routes = {}
        for sid, (s, dst) in nets.items():
            ox, oy = s.out_xy(); oy += 1                       # a wire point is drawn one cell above its y
            xs = chan_x[col(s) + 1] + pitch * tracks[col(s) + 1][sid]
            br = []
            for d, p in dst:
                ix, iy = d.in_xy(p); iy += 1
                if adjacent(s, d):
                    br.append([(xs, iy)] if iy != oy else [])
                else:
                    ly = lane_y[d.module] + pitch * lanes[d.module][sid]
                    xd = chan_x[col(d)] + pitch * tracks[col(d)][sid]
                    br.append([(xs, ly), (xd, ly), (xd, iy)])
                br[-1].append((d, p))
            self.routes[sid] = ((xs, oy), br)

    def segments(self):
        """Every drawn wire piece as (net id, (x1, y1), (x2, y2)), from the routes of layout()."""
        seg = []
        for sid, ((jx, jy), br) in self.routes.items():
            s = next(b for b in self.blocks if id(b) == sid)
            ox, oy = s.out_xy(); seg.append((sid, (ox, oy + 1), (jx, jy)))
            for path in br:
                last = (jx, jy)
                for q in path:
                    if isinstance(q[0], Block):
                        ix, iy = q[0].in_xy(q[1]); q = (ix, iy + 1)
                    seg.append((sid, last, q)); last = q
        return [g for g in seg if g[1] != g[2]]

    def overlaps(self):
        """Pairs of wire pieces of different nets that lie on top of each other (same line, shared length)."""
        seg, bad = self.segments(), []
        name = lambda sid: next(b for b in self.blocks if id(b) == sid).full_name or "?"
        for i, (n1, a1, b1) in enumerate(seg):
            for n2, a2, b2 in seg[i + 1:]:
                if n1 == n2:
                    continue
                for k in (0, 1):                                # k = the axis both pieces are constant on
                    if a1[k] == b1[k] == a2[k] == b2[k]:
                        lo = max(min(a1[1 - k], b1[1 - k]), min(a2[1 - k], b2[1 - k]))
                        hi = min(max(a1[1 - k], b1[1 - k]), max(a2[1 - k], b2[1 - k]))
                        if hi > lo:
                            bad.append((name(n1), name(n2), "xy"[k], a1[k], lo, hi))
        return bad

    def _title(self, text, x, y):
        t = Block(self, "COMENT", "", [text], "", "", False, None, 0)
        t.x, t.y = x, y
        self.blocks.append(t)

    # --- output ------------------------------------------------------------------------------------
    def text(self):
        if not hasattr(self, "routes"):
            self.layout()
        for i, b in enumerate(self.blocks, 1):
            b.id = i
        L = ["[Aut]", "#1,8,7", "{41,27"]
        L += [b.line() for b in self.blocks]
        def pts(path):
            return ";".join(f"{q[0].id},{q[1]}" if isinstance(q[0], Block) else f"{q[0]},{q[1]}" for q in path)
        for s, d, p in self.wires:                             # constant operators: one direct wire each
            if id(s) not in self.routes:
                L.append(f">{s.id}:0 = {{{{{d.id},{p}}}}}")
        for sid, ((jx, jy), br) in sorted(self.routes.items(), key=lambda kv: next(b.id for b in self.blocks if id(b) == kv[0])):
            src = next(b for b in self.blocks if id(b) == sid)
            if len(br) == 1:
                head = "" if len(br[0]) == 1 else f"{jx},{jy};"
                L.append(f">{src.id}:0 = {{{{{head}{pts(br[0])}}}}}")
            else:
                L.append(f">{src.id}:0 = {{{{{jx},{jy}" + "".join("{" + pts(x) + "}" for x in br) + "}}")
        L += ["}", "[Const]", "{"]
        L += [f"{n}~{fmt(v)}~'{u}'~1~1~''" for n, v, u in self.consts]
        L += ["}", "[Fin]"]
        return "\r\n".join(L) + "\r\n"

    def save(self, path):
        with open(path, "w", encoding="latin-1", newline="") as f:
            f.write(self.text())
        for n1, n2, axis, at, lo, hi in self.overlaps():
            print(f"warning: wires of {n1} and {n2} overlap at {axis} = {at}, {lo} ... {hi}", file=sys.stderr)
        return path

    def expected(self):
        """What an export of the loaded program must show: modules, constants, start values of parameter blocks."""
        par = {}
        for b in self.blocks:
            if b.typ in ("PVR", "PVB", "PVI") and b.public and b.name:
                par.setdefault(b.module, {})[b.name] = float(b.params[0])
        return {"modules": sorted({b.module for b in self.blocks if b.module}),
                "constants": {n: float(v) for n, v, _u in self.consts}, "parameters": par, "stats": self.stats()}

    def stats(self):
        real = [b for b in self.blocks if b.typ != "COMENT"]
        return {"blocks": len(real), "wires": len(self.wires), "constants": len(self.consts),
                "public": sum(1 for b in real if b.public),
                "modules": sorted({b.module for b in real if b.module})}


if __name__ == "__main__":
    p = Program("Blink")
    o = p.block("OSC", "Blink", params=[4, 2]); p.wire(o, p.block("BO", "BlinkOut"))
    sp = p.block("PVR", "SP", params=[21.5], public=True)
    hy = p.block("HYST", "Above20", params=[20, 19]); p.wire(sp, hy); p.wire(hy, p.block("BO", "Above20Out"))
    sys.stdout.write(p.text())
