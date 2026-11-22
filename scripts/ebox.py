#!/usr/bin/env python3
"""ebox.py - read a WorkStation export file (.xml) and what is packed inside it, and patch bindings into one.

    ebox.py tree   export.xml                  object tree with types, values and bindings
    ebox.py unpack export.xml outdir           program text (.aut), graphics (.tgml), script source (.txt), documents
    ebox.py binds  export.xml                  every binding: object, property -> target
    ebox.py values export.xml [regex]          the values the objects had when exported (not computed signals)
    ebox.py aut    program.aut                 summary of a program text: blocks by type, modules, HFBs, constants
    ebox.py xbk    backup.xbk outdir [name]    programs and graphics out of a server backup (name: only paths holding it)
    ebox.py bind   in.xml out.xml binds.json [/Server 1]
                                               write bindings into an export, for Ws-Import. binds.json:
                                               [["FB/MODULE", "TE1_IN", "/Server 1/Other/MOD/TE1"], ...]
                                               (object path inside the file, binding point, absolute target)

As a library: Export(path).objects() / .files() / .binds(), parse_aut(text), bind(...).
Format facts: ../reference/findings.md, sections "File formats" and "Production exports".
"""
import base64, gzip, json, os, posixpath, re, sys
import xml.etree.ElementTree as ET

FILE_EXT = {"AutFile": ".aut", "FILE": ".tgml", "File": ".bin", "BinFile": None, "MappingFile": None}


def _safe(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_") or "x"


class Export:
    def __init__(self, path):
        self.path = path
        self.root = ET.parse(path).getroot()
        self.meta = {c.tag: c.get("Value") for c in (self.root.find("MetaInformation") or [])}
        self.types = {t.get("Name"): t for t in (self.root.find("Types") or [])}

    def base(self, typ):
        """Built-in type behind a generated udt.* name (menta.Program, tgml.TGML, script.Program ...)."""
        t = self.types.get(typ)
        return t.get("Base") if t is not None else typ

    def objects(self):
        """(path, OI element) for every object, parents first."""
        out = []

        def walk(e, path):
            for c in e.findall("OI"):
                p = path + "/" + c.get("NAME")
                out.append((p, c)); walk(c, p)
        eo = self.root.find("ExportedObjects")
        if eo is not None:
            walk(eo, "")
        return out

    def files(self):
        """(object path, parameter name, bytes) for every file held by a type: program text, graphic, document.
        A Script program gives ('.../name', 'Script', source)."""
        owner = {}
        for p, oi in self.objects():
            owner.setdefault(oi.get("TYPE"), p)
        for name, t in self.types.items():
            who = owner.get(name, "/" + name)
            for par in t.iter("Parameter"):
                iv = par.find("InitValue")
                if iv is None:
                    continue
                fc = iv.find("FileContents")
                if fc is not None and fc.text:
                    raw = base64.b64decode(fc.text)
                    try:
                        raw = gzip.decompress(raw)
                    except OSError:
                        pass
                    yield who, par.get("Name"), raw
                elif t.get("Base") == "script.Program" and par.get("Name") == "File" and iv.get("Value"):
                    code = ET.fromstring(iv.get("Value")).find("Code")
                    if code is not None and code.text:
                        yield who, "Script", base64.b64decode(code.text)

    def binds(self):
        """(object path, binding point, target object, target property). Targets as stored: relative to the object."""
        for p, oi in self.objects():
            for pi in oi.findall("PI"):
                r = pi.find("Reference")
                if r is not None and r.get("Object"):
                    yield p, pi.get("Name"), r.get("Object"), r.get("Property") or ""


# ---- program text -----------------------------------------------------------------------------------------------
BLOCK = re.compile(r'#(\d+)\s+"([^"]*)"\s+\[(-?\d+),(-?\d+),(\d+),(\d+)\]\s+(.*?)\s=\s(\S+)\s?(.*)$')


class AutBlock:
    def __init__(self, m):
        self.id, self.name, self.x, self.y = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
        self.flag, self.meta, self.typ, self.par = int(m.group(6)), m.group(7), m.group(8), m.group(9)
        self.sub = None                                         # Scope of an HFB

    public = property(lambda s: bool(s.flag & 1)); rw = property(lambda s: bool(s.flag & 2))
    backup = property(lambda s: bool(s.flag & 4))


class Scope:
    """One diagram level: the program, or the inside of an HFB. Block ids are local to it."""
    def __init__(self):
        self.blocks, self.wires, self.frames = {}, [], []

    def walk(self, path=""):
        yield path, self
        for b in self.blocks.values():
            if b.sub:
                yield from b.sub.walk(path + "/" + (b.name or "HFB"))


def _branches(txt):
    """Wire body between the outer braces -> [(corner points, destination block id, pin)]; None, None = open end."""
    out = []

    def walk(s, prefix):
        i = s.find("{")
        head = s if i < 0 else s[:i]
        pts = [tuple(int(v) for v in p.rstrip(".").split(",")) for p in head.split(";") if p]
        if i < 0:
            out.append((prefix + pts, None, None) if head.endswith(".") else (prefix + pts[:-1], pts[-1][0], pts[-1][1]))
            return
        split(s[i:], prefix + pts)

    def split(s, prefix):
        depth = 0
        for k, c in enumerate(s):
            if c == "{":
                if depth == 0:
                    st = k + 1
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    walk(s[st:k], prefix)
    split(txt, [])
    return out


def parse_aut(text):
    """-> (Scope, constants [(name, value, unit, public)], bindings [(constant, path)], cycle ms or None)."""
    L = text.replace("\r\n", "\n").split("\n")

    def scope(i):
        sc, last = Scope(), None
        while i < len(L):
            l = L[i]; m = BLOCK.match(l)
            if m:
                last = AutBlock(m); sc.blocks[last.id] = last
            elif l.strip() == "{" and last is not None and last.typ == "HFB":
                last.sub, i = scope(i + 1)
            elif l.startswith(">"):
                w = re.match(r">(\d+):(\d+) = \{(.*)\}$", l)
                if w:
                    sc.wires.append((int(w.group(1)), int(w.group(2)), _branches(w.group(3))))
                else:
                    sc.frames.append(l)                         # ">0 = x,y,N {{...}}": a drawn frame, no signal
            elif l.strip() == "}" or l.startswith("["):
                return sc, i
            i += 1
        return sc, i
    top, _ = scope(L.index("[Aut]") + 3)

    def section(name):
        if name not in L:
            return []
        i = L.index(name) + 1; out = []
        while i < len(L) and not L[i].startswith("["):
            if L[i] not in ("{", "}", ""):
                out.append(L[i])
            i += 1
        return out
    consts = []
    for l in section("[Const]"):
        f = l.split("~")
        if len(f) >= 4:
            consts.append((f[0], f[1], f[2].strip("'"), f[3] == "1"))
    binds = [tuple(l.split(";", 1)) for l in section("[InitialBindings]") if ";" in l]
    ral = section("[Ral]"); cyc = None
    for l in ral:
        m = re.match(r"\d+,(\d+)$", l)
        if m:
            cyc = int(m.group(1))
    return top, consts, binds, cyc


def aut_summary(text):
    top, consts, binds, cyc = parse_aut(text)
    types, mods, hfb, n, pub, alarms = {}, set(), [], 0, 0, []
    for path, sc in top.walk():
        if path:
            hfb.append(path)
        for b in sc.blocks.values():
            if b.typ in ("COMENT", "HFB"):
                continue
            n += 1; types[b.typ] = types.get(b.typ, 0) + 1; pub += b.public
            if "\\" in b.name:
                mods.add(b.name.split("\\")[0])
            if b.typ == "ALARM":
                alarms.append(b.name)
    L = [f"blocks {n}, public {pub}, constants {len(consts)} ({sum(1 for c in consts if not c[3])} private), "
         f"cycle {cyc} ms", "modules: " + ", ".join(sorted(mods)),
         "types: " + ", ".join(f"{k} {v}" for k, v in sorted(types.items(), key=lambda kv: -kv[1]))]
    if hfb:
        L.append("HFB: " + ", ".join(hfb))
    if alarms:
        L.append("alarm blocks: " + ", ".join(alarms))
    if binds:
        L.append("constants bound in the file: " + ", ".join(f"{a} <- {b}" for a, b in binds))
    return "\n".join(L)


# ---- bindings into a file ---------------------------------------------------------------------------------------
def bind(src, dst, pairs, parent="/Server 1"):
    """Write bindings into an export so that Ws-Import brings the object in already bound.

    pairs: (object path inside the file, binding point, absolute target 'object path/property').
    parent: where the file will be imported; targets are stored relative to the object that holds the point.
    Export the object in Special mode first: only then the file keeps the bindings it already has."""
    tree = ET.parse(src); root = tree.getroot()
    idx = {}

    def walk(e, path):
        for c in e.findall("OI"):
            p = path + "/" + c.get("NAME"); idx[p] = c; walk(c, p)
    walk(root.find("ExportedObjects"), "")
    for obj, point, target in pairs:
        oi = idx.get("/" + obj.strip("/"))
        if oi is None:
            raise KeyError(f"no object {obj} in {src}")
        t_obj, t_prop = target.rsplit("/", 1)
        rel = posixpath.relpath(t_obj, posixpath.join(parent, obj.strip("/")))
        pi = next((p for p in oi.findall("PI") if p.get("Name") == point), None)
        if pi is None:
            pi = ET.Element("PI", {"Name": point}); oi.insert(0, pi)
        for r in pi.findall("Reference"):
            pi.remove(r)
        pi.attrib.pop("Value", None)
        ET.SubElement(pi, "Reference", {"DeltaFilter": "0", "Object": rel, "Property": t_prop, "Retransmit": "0",
                                        "TransferRate": "10"})
    for tag in ("ExportMode",):                                 # a Standard file would be read without outside targets
        root.set(tag, "Special")
        m = root.find("MetaInformation/" + tag)
        if m is not None:
            m.set("Value", "Special")
    import io
    buf = io.BytesIO(); tree.write(buf, encoding="UTF-8", xml_declaration=True)
    # The import reads an embedded file only from a CDATA section ("Empty binary file" otherwise); the XML
    # library writes plain text, so the sections are put back.
    text = re.sub(r"(<FileContents\b[^>]*>)([^<]+)(</FileContents>)", r"\1<![CDATA[\2]]>\3", buf.getvalue().decode("utf-8"))
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return len(pairs)


# ---- server backup ---------------------------------------------------------------------------------------------
def xbk_unpack(path, out, only=""):
    """A backup (.xbk) is a zip. Program text and graphics are members UDT/pu/udt/<a>/<b>___AutFile.cdata and
    ...___FILE.cdata: plain gzip, named after the object's type udt.<a>.<b>. Which object has that type is in
    Configuration/configuration.db, table ObjectInstance (Id, ParentId, TypeName, NAME). Nothing else is read:
    the same database holds the user accounts."""
    import sqlite3, tempfile, zipfile
    z = zipfile.ZipFile(path); os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        db = z.extract("Configuration/configuration.db", tmp)
        con = sqlite3.connect(db)
        rows = {r[0]: r[1:] for r in con.execute("SELECT Id, ParentId, TypeName, NAME FROM ObjectInstance")}
        con.close()
    def full(i):
        parts = []
        while i in rows and len(parts) < 40:
            parts.append(rows[i][2] or ""); i = rows[i][0]
        return "/".join(reversed(parts))
    by_type = {}
    for i, (_p, typ, _n) in rows.items():
        if typ and typ.startswith("udt."):
            by_type.setdefault(typ, full(i))
    done = []
    for m in z.namelist():
        k = re.match(r"UDT/pu/udt/([^/]+)/([^/]+?)___(AutFile|FILE)\.cdata$", m)
        if not k:
            continue
        who = by_type.get(f"udt.{k.group(1)}.{k.group(2)}", f"{k.group(1)}.{k.group(2)}")
        if only and only not in who:
            continue
        raw = z.read(m)
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
        fn = os.path.join(out, _safe(who.strip("/").replace("/", "__")) + (".aut" if k.group(3) == "AutFile" else ".tgml"))
        open(fn, "wb").write(raw); done.append((who, fn, len(raw)))
    return done


# ---- command line -----------------------------------------------------------------------------------------------
def main(a):
    if len(a) < 2:
        print(__doc__); return 2
    cmd = a[0]
    if cmd == "aut":
        raw = open(a[1], "rb").read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        print(aut_summary(text)); return 0
    if cmd == "xbk":
        for who, fn, n in sorted(xbk_unpack(a[1], a[2], a[3] if len(a) > 3 else "")):
            print(f"{who}  ->  {fn}  ({n} bytes)")
        return 0
    if cmd == "bind":
        n = bind(a[1], a[2], json.load(open(a[3])), a[4] if len(a) > 4 else "/Server 1")
        print(f"{n} bindings written to {a[2]}"); return 0
    ex = Export(a[1])
    if cmd == "tree":
        print(f"{os.path.basename(a[1])}: mode {ex.meta.get('ExportMode')}, version {ex.meta.get('SourceVersion')}, "
              f"from {ex.meta.get('ServerFullPath')}")
        for p, oi in ex.objects():
            if oi.get("hidden") == "1":
                continue
            pis = oi.findall("PI"); nb = sum(1 for x in pis if x.find("Reference") is not None)
            print(f"{'  ' * (p.count('/') - 1)}{oi.get('NAME')}  [{ex.base(oi.get('TYPE'))}]"
                  + (f"  {len(pis)} values" if pis else "") + (f", {nb} bound" if nb else ""))
    elif cmd == "values":                                       # live values at the moment of the export
        pat = a[2] if len(a) > 2 else ""
        for p, oi in ex.objects():
            for pi in oi.findall("PI"):
                if pi.get("Value") is not None and not re.match(r"[0-9A-F]{8}-", pi.get("Name")):
                    line = f"{p}/{pi.get('Name')} = {pi.get('Value')}"
                    if re.search(pat, line):
                        print(line)
    elif cmd == "binds":
        for p, point, obj, prop in ex.binds():
            print(f"{p} . {point}  <-  {obj}" + (f" . {prop}" if prop else ""))
    elif cmd == "unpack":
        out = a[2]; os.makedirs(out, exist_ok=True)
        for who, par, raw in ex.files():
            ext = ".txt" if par == "Script" else FILE_EXT.get(par, ".bin")
            if ext is None:
                continue                                        # compiled code and its map: of no use as files
            if ext == ".bin" and raw[:4] == b"%PDF":
                ext = ".pdf"
            fn = os.path.join(out, _safe(who.strip("/").replace("/", "__")) + ext)
            open(fn, "wb").write(raw)
            line = f"{fn}  ({len(raw)} bytes)"
            if ext == ".aut":
                try:
                    line += "\n    " + aut_summary(raw.decode("utf-8", "replace")).replace("\n", "\n    ")
                except Exception as e:                          # a text this reader does not know: keep the file
                    line += f"\n    (not summarised: {e})"
            print(line)
    else:
        print(__doc__); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
