# -*- coding: utf-8 -*-
"""Stage rebuild pass 2: wipe, rebuild, size-driven prune, provenance fixes."""
import shutil, os, time, subprocess, hashlib, json

STAGE = r"D:\zcode-skill-mcp-backup"
BUILDER = r"D:\glm生成计划\claude-video\audit_work\build_backup.py"

for i in range(4):
    try:
        shutil.rmtree(STAGE); break
    except Exception as e:
        print("wipe retry", i, e)
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", STAGE])
        time.sleep(1)
print("cleared:", not os.path.exists(STAGE))
subprocess.run(["python", BUILDER], check=True)

def dsize(root):
    return sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fn in os.walk(root) for f in fn)

def dh(root):
    h = hashlib.sha256()
    for dp, dn, fn in sorted(os.walk(root)):
        for f in sorted(fn):
            h.update(os.path.relpath(os.path.join(dp, f), root).encode())
            h.update(hashlib.sha256(open(os.path.join(dp, f), "rb").read()).hexdigest().encode())
    return h.hexdigest()

localdir = os.path.join(STAGE, "skills", "local")
heavy = [n for n in os.listdir(localdir)
         if os.path.isdir(os.path.join(localdir, n)) and dsize(os.path.join(localdir, n)) > 5_000_000]
for name in heavy:
    d = os.path.join(localdir, name)
    print("pruning heavy dir:", name, "%.0f MB" % (dsize(d) / 1048576))
    for p in [".git", os.path.join("assets", "audio"), os.path.join("assets", "video"),
              os.path.join("template", "public"), os.path.join("template", "out"),
              os.path.join("template", "build"), "node_modules"]:
        shutil.rmtree(os.path.join(d, p), ignore_errors=True)

removed = 0
for dp, dn, fn in os.walk(STAGE):
    for d in list(dn):
        if d == ".git":
            shutil.rmtree(os.path.join(dp, d), ignore_errors=True); dn.remove(d); removed += 1
    for f in fn:
        fp = os.path.join(dp, f)
        if f.endswith((".mp3", ".wav", ".mp4", ".mov", ".webm", ".zip", ".exe", ".pack", ".idx")) \
                or os.path.getsize(fp) > 2_000_000:
            os.remove(fp); removed += 1
print("global prune removed:", removed)

mp = os.path.join(STAGE, "MANIFEST.json")
m = json.load(open(mp, encoding="utf-8"))
for it in m["skills"]:
    op = it.get("original_path", "")
    if "video-shotcraft" in op or "video-shotcraft" in op:
        d = os.path.join(localdir, os.path.basename(op.rstrip("\\/")))
        it.update(size_bytes=dsize(d), sha256_dir=dh(d),
                  source="github.com/Vincentwei1021/video-shotcraft (Apache-2.0, 10k+ stars; local git clone, last commit by lynnx 2026-09-24)",
                  license="Apache-2.0 for CODE (notice kept); bundled media assets NOT redistributed",
                  note="assets/audio, template/public textures and .git history excluded from public archive")
    elif "mmc-helper" in op:
        it.update(source="github.com/shangyu-xiong/mmc-helper (MIT; local git clone, last commit by shangyu-xiong 2026-09-20)",
                  license="MIT (notice kept in THIRD-PARTY-NOTICE.md)")
json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

with open(os.path.join(STAGE, "skills", "local", "THIRD-PARTY-NOTICE.md"), "a", encoding="utf-8") as f:
    f.write("""
## mmc-helper

- Source: https://github.com/shangyu-xiong/mmc-helper
- License: MIT (verified via GitHub API 2026-10-02). Upstream copyright remains with the author.
- Local copy is a git clone (last upstream commit 2026-09-20); .git history excluded.

## video-shotcraft

- Source: https://github.com/Vincentwei1021/video-shotcraft
- License: Apache-2.0 (verified via GitHub API 2026-10-02) for CODE.
- The bundled media assets (assets/audio BGM/SFX, template/public textures) are NOT covered
  by the upstream code license and are NOT included in this archive.
- .git history excluded; this is a source snapshot.
""")

with open(os.path.join(STAGE, "skills", "manifests", "streamlit.md"), "w", encoding="utf-8") as f:
    f.write(
        "# developing-with-streamlit (manifest only - source NOT redistributed)\n\n"
        "- Original local path: C:/Users/FAJ/.zcode/skills/streamlit/SKILL.md\n"
        "- Type: routing skill (19.5 KB single SKILL.md)\n"
        "- Provenance: UNVERIFIED. Style matches Anthropic's official skill family, but origin could\n"
        "  not be confirmed and the anthropics/skills repo carries no license file, so redistribution\n"
        "  rights are unclear. The full text is therefore NOT included in this public archive.\n"
        "- SHA-256(SKILL.md): see MANIFEST.json entry.\n"
        "- Removal reason: third-party, license unclear, not in keep-set.\n"
        "- Restore: reinstall from your original source, or recreate from docs.streamlit.io.\n")

total = dsize(STAGE)
print("stage total: %.2f MB" % (total / 1048576))
print("skills/local entries:", len(os.listdir(localdir)))
big = [os.path.join(dp, f) for dp, dn, fn in os.walk(STAGE) for f in fn
       if os.path.getsize(os.path.join(dp, f)) > 1_000_000]
print("files >1MB remaining:", big if big else "none")
