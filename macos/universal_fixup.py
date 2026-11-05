#!/usr/bin/env python3
"""
TEE Encryption - make the macOS app truly universal (Apple Silicon + Intel)

`flet build macos` installs the Python packages once per architecture and merges
both installs with `lipo` - but only files that end in `.so`. Native libraries that
wheels bundle as `.dylib` (e.g. Pillow's PIL/.dylibs/libjpeg.62.4.0.dylib) are copied
from the arm64 install only. On an Intel Mac `import PIL` would then fail.

This script
  1. finds every Mach-O file inside the Python site-packages of the built app,
  2. downloads the x86_64 wheels of the affected packages (exact same versions),
  3. merges the missing x86_64 slices in with `lipo`,
  4. checks that every @loader_path / @rpath dependency of those binaries exists,
  5. re-signs the changed code (ad-hoc) and verifies the app signature, and
  6. fails if ANY Mach-O file in the whole app still lacks arm64 or x86_64.

Usage:
  python3 universal_fixup.py "<path>/TEE Encryption.app" <work-dir>
          [--python-version 3.12] [--min-macos 11.0] [--check-only]
"""

import argparse
import email.parser
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REQUIRED_ARCHS = {"arm64", "x86_64"}

MACHO_MAGICS = {
    b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",  # 32-bit
    b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",  # 64-bit
    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",  # fat (universal)
    b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",  # fat64
}

BUNDLE_SUFFIXES = (".framework", ".bundle", ".app", ".appex", ".xpc", ".plugin")


def log(msg):
    print(msg, flush=True)


def run(cmd, check=True, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if check and result.returncode != 0:
        out = (result.stdout or "") + (result.stderr or "")
        raise SystemExit(f"[FEHLER] Befehl fehlgeschlagen ({result.returncode}): {' '.join(map(str, cmd))}\n{out}")
    return result


def is_macho(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return False
    if len(head) < 8 or head[:4] not in MACHO_MAGICS:
        return False
    if head[:4] == b"\xca\xfe\xba\xbe":
        # Java .class files share this magic - a real fat header has a small arch count
        nfat = int.from_bytes(head[4:8], "big")
        if nfat == 0 or nfat > 20:
            return False
    return True


def archs_of(path: Path) -> set:
    result = run(["lipo", "-archs", str(path)], check=False)
    if result.returncode != 0:
        return set()
    return set(result.stdout.split())


def walk_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            p = Path(dirpath) / name
            if not p.is_symlink():
                yield p


def find_site_packages(app: Path):
    found = []
    for dirpath, dirnames, filenames in os.walk(app, followlinks=False):
        if os.path.basename(dirpath) == "site-packages" and not os.path.islink(dirpath):
            found.append(Path(dirpath))
    return found


def read_distributions(site_packages: Path):
    """Maps every file listed in a RECORD to its distribution (name, version, is_pure)."""
    owners = {}
    dists = []
    for info in site_packages.glob("*.dist-info"):
        meta_file = info / "METADATA"
        if not meta_file.exists():
            continue
        with open(meta_file, encoding="utf-8", errors="replace") as f:
            meta = email.parser.Parser().parse(f, headersonly=True)
        name, version = meta.get("Name"), meta.get("Version")
        tags = []
        wheel_file = info / "WHEEL"
        if wheel_file.exists():
            with open(wheel_file, encoding="utf-8", errors="replace") as f:
                tags = [line.split(":", 1)[1].strip() for line in f if line.startswith("Tag:")]
        is_pure = bool(tags) and all(t.endswith("-any") for t in tags)
        dist = {"name": name, "version": version, "tags": tags, "pure": is_pure}
        dists.append(dist)
        record = info / "RECORD"
        if record.exists():
            with open(record, encoding="utf-8", errors="replace") as f:
                for line in f:
                    rel = line.split(",", 1)[0].strip()
                    if rel:
                        owners[os.path.normpath(rel)] = dist
    return dists, owners


def download_x86_wheel(python, dist, dest: Path, py_version: str, min_macos: str) -> Path:
    plat = "macosx_{}_x86_64".format(min_macos.replace(".", "_"))
    abi = "cp" + py_version.replace(".", "")
    before = set(dest.glob("*.whl"))
    cmd = [
        python, "-m", "pip", "download", "--disable-pip-version-check", "--no-deps",
        "--only-binary=:all:", "--platform", plat,
        "--python-version", py_version, "--implementation", "cp",
        "--abi", abi, "--abi", "abi3", "--abi", "none",
        "-d", str(dest), f"{dist['name']}=={dist['version']}",
    ]
    log(f"  -> lade x86_64-Wheel: {dist['name']}=={dist['version']} ({plat})")
    run(cmd, capture=False)
    new = set(dest.glob("*.whl")) - before
    if not new:
        # already downloaded in an earlier run
        norm = dist["name"].lower().replace("-", "_")
        new = {w for w in dest.glob("*.whl")
               if w.name.lower().startswith(f"{norm}-{dist['version']}-")}
    if not new:
        raise SystemExit(f"[FEHLER] Kein x86_64-Wheel fuer {dist['name']}=={dist['version']} gefunden.")
    return sorted(new)[0]


def thin_copy(src: Path, arch: str, tmpdir: Path) -> Path:
    archs = archs_of(src)
    if archs == {arch}:
        return src
    out = tmpdir / f"{src.name}.{arch}"
    run(["lipo", str(src), "-thin", arch, "-output", str(out)])
    return out


def install_name(binary: Path, arch: str):
    """LC_ID_DYLIB of a dylib (otool -L lists it like a dependency - it is none)."""
    out = run(["otool", "-arch", arch, "-D", str(binary)], check=False).stdout or ""
    lines = [line.strip() for line in out.splitlines()[1:] if line.strip()]
    return lines[0] if lines else None


def loader_dependencies(binary: Path):
    """@loader_path/@rpath dependencies of a binary (per x86_64 and arm64 slice)."""
    deps = set()
    for arch in sorted(archs_of(binary) & REQUIRED_ARCHS):
        own_id = install_name(binary, arch)
        out = run(["otool", "-arch", arch, "-L", str(binary)], check=False).stdout or ""
        for line in out.splitlines()[1:]:
            dep = line.strip().split(" (")[0]
            if dep == own_id:
                continue
            if dep.startswith("@loader_path/") or dep.startswith("@rpath/"):
                deps.add((arch, dep))
    return deps


def rpaths_of(binary: Path, arch: str):
    out = run(["otool", "-arch", arch, "-l", str(binary)], check=False).stdout or ""
    paths, lines = [], out.splitlines()
    for i, line in enumerate(lines):
        if "cmd LC_RPATH" in line:
            for follow in lines[i + 1:i + 4]:
                follow = follow.strip()
                if follow.startswith("path "):
                    paths.append(follow[5:].split(" (offset")[0])
    return paths


def check_dependencies(binaries, app: Path):
    """Every @loader_path/@rpath dependency must exist and contain the needed arch."""
    problems = []
    for binary in binaries:
        for arch, dep in loader_dependencies(binary):
            candidates = []
            if dep.startswith("@loader_path/"):
                candidates.append(binary.parent / dep[len("@loader_path/"):])
            else:
                rest = dep[len("@rpath/"):]
                for rp in rpaths_of(binary, arch):
                    if rp.startswith("@loader_path"):
                        rp = str(binary.parent) + rp[len("@loader_path"):]
                    elif rp.startswith("@executable_path"):
                        rp = str(app / "Contents" / "MacOS") + rp[len("@executable_path"):]
                    candidates.append(Path(rp) / rest)
            resolved = next((c for c in candidates if c.exists()), None)
            if resolved is None:
                # @rpath refs to the app's own frameworks are resolved by the main executable
                if dep.startswith("@rpath/") and (app / "Contents" / "Frameworks" / dep[len("@rpath/"):]).exists():
                    continue
                problems.append(f"{binary} [{arch}] -> {dep} (nicht gefunden)")
            elif arch not in archs_of(resolved.resolve()):
                problems.append(f"{binary} [{arch}] -> {resolved} (ohne {arch})")
    return problems


def remove_external_symlinks(app: Path):
    """
    Removes symlinks that point OUTSIDE the app bundle. serious_python leaves such a
    build-time link in site-packages (`.pod` -> its CocoaPods folder). codesign rejects
    it ("invalid destination for symbolic link in bundle"), and Gatekeeper reports
    downloaded apps with an invalid seal as "damaged". The app never uses these links.
    """
    app_real = app.resolve()
    removed = []
    for dirpath, dirnames, filenames in os.walk(app, followlinks=False):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            if not p.is_symlink():
                continue
            target = os.readlink(p)
            resolved = (Path(target) if os.path.isabs(target) else p.parent / target).resolve()
            try:
                resolved.relative_to(app_real)
                continue  # internal link (e.g. Versions/Current -> A) - keep it
            except ValueError:
                pass
            log(f"  entferne Symlink nach ausserhalb: {p.relative_to(app.parent)} -> {target}")
            p.unlink()
            removed.append(p)
    return removed


def is_signed_bundle(bundle: Path) -> bool:
    if any((bundle / p).exists() for p in ("Contents/_CodeSignature", "_CodeSignature")):
        return True
    # frameworks: Versions/A/_CodeSignature (Versions/Current is a symlink to it)
    return any(bundle.glob("Versions/*/_CodeSignature"))


def resign(app: Path, changed, removed=()):
    """Re-signs changed Mach-O files, then every signed bundle containing a change
    (innermost first) and finally the app itself - keeping identifier/entitlements."""
    if not changed and not removed:
        return
    log(f"Signiere neu (ad-hoc): {len(changed)} geaenderte Binaerdatei(en), "
        f"{len(removed)} entfernte Symlink(s) ...")
    for f in changed:
        run(["codesign", "--force", "--sign", "-", "--timestamp=none", str(f)])
    bundles = set()
    for f in list(changed) + list(removed):
        p = f.parent
        while p != app and p != p.parent:
            if p.suffix in BUNDLE_SUFFIXES and is_signed_bundle(p):
                bundles.add(p)
            p = p.parent
    preserve = "--preserve-metadata=identifier,entitlements,flags,runtime"
    for b in sorted(bundles, key=lambda p: len(p.parts), reverse=True):
        log(f"  re-sign {b.relative_to(app.parent)}")
        run(["codesign", "--force", "--sign", "-", "--timestamp=none", preserve, str(b)])
    log(f"  re-sign {app.name}")
    run(["codesign", "--force", "--sign", "-", "--timestamp=none", preserve, str(app)])


def verify_signature(app: Path):
    result = run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)], check=False)
    out = ((result.stdout or "") + (result.stderr or "")).strip()
    # keep only the interesting lines (codesign lists every validated framework)
    lines = [line for line in out.splitlines()
             if not line.startswith(("--prepared:", "--validated:"))]
    return result.returncode == 0, "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("app", type=Path)
    parser.add_argument("work_dir", type=Path)
    parser.add_argument("--python-version", default="3.12", help="Python version embedded in the app")
    parser.add_argument("--min-macos", default="11.0", help="Minimum macOS version of the app")
    parser.add_argument("--check-only", action="store_true", help="Only verify, change nothing")
    args = parser.parse_args()

    app = args.app.resolve()
    if not (app / "Contents" / "Info.plist").exists():
        raise SystemExit(f"[FEHLER] Kein App-Bundle: {app}")
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)

    ok, out = verify_signature(app)
    log(f"Signatur vor der Bearbeitung: {'OK' if ok else 'FEHLER'}" + ("" if ok else f"\n{out}"))

    removed = [] if args.check_only else remove_external_symlinks(app)

    changed, added = [], []
    site_dirs = find_site_packages(app)
    log(f"site-packages im App-Bundle: {len(site_dirs)}")
    for sp in site_dirs:
        log(f"- {sp.relative_to(app.parent)}")
        dists, owners = read_distributions(sp)
        thin = []
        for f in walk_files(sp):
            if is_macho(f):
                missing = REQUIRED_ARCHS - archs_of(f)
                if missing:
                    thin.append((f, missing))
        if not thin:
            log("  alle Binaerdateien sind bereits universal (arm64 + x86_64)")
            continue
        log(f"  {len(thin)} Binaerdatei(en) ohne x86_64 bzw. arm64:")
        for f, missing in thin:
            log(f"    {f.relative_to(sp)}  (fehlt: {', '.join(sorted(missing))})")
        if args.check_only:
            continue

        need = {}
        for f, missing in thin:
            if "x86_64" not in missing:
                raise SystemExit(f"[FEHLER] {f} hat kein arm64 - das darf nach flet build nicht vorkommen.")
            dist = owners.get(os.path.normpath(str(f.relative_to(sp))))
            if dist is None:
                raise SystemExit(f"[FEHLER] {f} gehoert zu keinem installierten Paket (RECORD).")
            need[(dist["name"], dist["version"])] = dist

        dl_dir = work / "x86_64-wheels"
        dl_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as tmp:
            tmpdir = Path(tmp)
            for dist in need.values():
                wheel = download_x86_wheel(sys.executable, dist, dl_dir, args.python_version, args.min_macos)
                unpacked = tmpdir / wheel.stem
                with zipfile.ZipFile(wheel) as z:
                    z.extractall(unpacked)
                for xf in walk_files(unpacked):
                    if not is_macho(xf) or "x86_64" not in archs_of(xf):
                        continue
                    rel = xf.relative_to(unpacked)
                    target = sp / rel
                    if target.exists():
                        if "x86_64" in archs_of(target):
                            continue
                        merged = tmpdir / f"{target.name}.universal"
                        run(["lipo", "-create", str(thin_copy(target, "arm64", tmpdir)),
                             str(thin_copy(xf, "x86_64", tmpdir)), "-output", str(merged)])
                        shutil.copymode(target, merged)
                        os.replace(merged, target)
                        changed.append(target)
                        log(f"    + x86_64 ergaenzt: {rel}")
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(xf, target)
                        added.append(target)
                        changed.append(target)
                        log(f"    + x86_64-Datei hinzugefuegt: {rel}")

        # dependencies of everything we touched (and of the extension modules next to it)
        deps_problems = check_dependencies(
            [f for f in walk_files(sp) if is_macho(f)], app)
        if deps_problems:
            log("[FEHLER] Fehlende Abhaengigkeiten:")
            for p in deps_problems:
                log(f"    {p}")
            raise SystemExit(1)

    if (changed or removed) and not args.check_only:
        resign(app, changed, removed)

    # final verification over the WHOLE app
    log("Pruefe alle Mach-O-Dateien im App-Bundle ...")
    total, problems = 0, []
    added_set = {p.resolve() for p in added}
    for f in walk_files(app):
        if not is_macho(f):
            continue
        total += 1
        missing = REQUIRED_ARCHS - archs_of(f)
        if missing and f.resolve() not in added_set:
            problems.append(f"{f.relative_to(app.parent)}  (fehlt: {', '.join(sorted(missing))})")
    log(f"  {total} Mach-O-Dateien geprueft")
    if problems:
        log("[FEHLER] Nicht universelle Binaerdateien:")
        for p in problems:
            log(f"    {p}")
        raise SystemExit(1)
    log("  OK - jede Binaerdatei enthaelt arm64 UND x86_64")

    ok, out = verify_signature(app)
    if not ok:
        log(f"[FEHLER] Signaturpruefung fehlgeschlagen:\n{out}")
        raise SystemExit(1)
    log("Signatur: OK (codesign --verify --deep --strict)")


if __name__ == "__main__":
    main()
