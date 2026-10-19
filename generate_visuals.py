"""
generate_visuals.py — Generates visual architecture diagrams for the Encrypted SQLite System
using the Rust-accelerated Feather 2D Graphics Engine.
"""

import os
from pathlib import Path
import feather
from feather import Canvas, ui, Font

def render_system_visual():
    print("[Feather Engine] Rendering Encrypted SQLite v2 Architecture Infographic...")
    
    root_dir = Path(__file__).parent
    assets_dir = root_dir / "docs" / "images"
    assets_dir.mkdir(parents=True, exist_ok=True)
    out_path = assets_dir / "architecture_v2.png"
    assets_root = root_dir / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)
    out_path_root = assets_root / "architecture_v2.png"

    width, height = 1440, 960
    canvas = Canvas(width, height, background="#0c1017")
    font = Font.default_font()

    # 1. Subtle Ambient Backdrop Glows
    canvas.draw_circle(250.0, 180.0, 350.0, fill="rgba(56, 189, 248, 0.04)")
    canvas.draw_circle(720.0, 480.0, 400.0, fill="rgba(168, 85, 247, 0.03)")
    canvas.draw_circle(1180.0, 750.0, 380.0, fill="rgba(34, 197, 94, 0.03)")

    # 2. Subtle Grid
    for x in range(0, width, 40):
        canvas.draw_line(float(x), 0.0, float(x), float(height), stroke="rgba(255, 255, 255, 0.015)", stroke_width=1.0)
    for y in range(0, height, 40):
        canvas.draw_line(0.0, float(y), float(width), float(y), stroke="rgba(255, 255, 255, 0.015)", stroke_width=1.0)

    # 3. Header Title Block
    canvas.draw_rounded_rect(40.0, 30.0, 1360.0, 85.0, rx=14.0, fill="#131926", stroke="#26334d", stroke_width=1.5)
    canvas.draw_text("ENCRYPTED SQLITE SYSTEM v2.0", 65.0, 48.0, size=24.0, color="#ffffff", font=font)
    canvas.draw_text("HIGH-PERFORMANCE TWO-TIER CACHING & AEAD CRYPTOGRAPHIC DOCUMENT STORE", 65.0, 82.0, size=12.0, color="#7dd3fc", font=font)

    # Top right security badges
    canvas.draw_rounded_rect(1090.0, 48.0, 130.0, 32.0, rx=8.0, fill="rgba(56, 189, 248, 0.15)", stroke="#38bdf8", stroke_width=1.0)
    canvas.draw_text("AES-256-GCM", 1108.0, 58.0, size=11.0, color="#38bdf8", font=font)

    canvas.draw_rounded_rect(1235.0, 48.0, 145.0, 32.0, rx=8.0, fill="rgba(168, 85, 247, 0.15)", stroke="#a855f7", stroke_width=1.0)
    canvas.draw_text("CHACHA20-POLY", 1245.0, 58.0, size=11.0, color="#c084fc", font=font)

    # 4. KPI Telemetry Bar
    telemetry_card = ui.Card(
        width=1360.0,
        padding=18.0,
        corner_radius=12.0,
        background="rgba(255, 255, 255, 0.025)",
        border_color="rgba(255, 255, 255, 0.08)",
    )
    kpi_row = ui.Row(gap=22.0)
    kpi_row.add(ui.Metric("< 0.007 ms", label="L1 Memory Read", trend="10.1x Baseline"))
    kpi_row.add(ui.Metric("322,580", label="Write-Behind Ops/sec", trend="+20.5x Speedup"))
    kpi_row.add(ui.Metric("< 0.0001 ms", label="Bloom 0-Disk Miss", trend="1,000,000+ ops/sec"))
    kpi_row.add(ui.Metric("600,000", label="PBKDF2 Rounds", trend="Argon2id/SHA256"))
    kpi_row.add(ui.Metric("75% - 90%", label="Zstandard Shrink", trend="ZSTD / ZLIB"))
    telemetry_card.add(kpi_row)
    telemetry_card.render(canvas, 40.0, 135.0)

    # 5. Core 3-Column Architecture Cards
    # COLUMN 1: Tier 1 - L1 Caching Engine (x=40, y=240, w=430)
    c1 = ui.Card(
        width=430.0,
        padding=22.0,
        corner_radius=16.0,
        background="#111722",
        border_color="rgba(56, 189, 248, 0.35)",
        shadow_blur=20.0,
        shadow_color="rgba(0, 0, 0, 0.4)"
    )
    c1.add(ui.Text("## [Tier 1] L1 Caching Layer", size=17.0, color="#38bdf8"))
    c1.add(ui.Text("Sub-millisecond negative and positive cache in RAM", size=11.0, color="#94a3b8"))
    c1.add(ui.Divider(thickness=1.0, color="rgba(255, 255, 255, 0.08)", margin=6.0))

    c1.add(ui.Text(
        "• **MemoryL1Adapter**: Thread-safe LRU in RAM (<0.01ms)\n"
        "• **CompressedMemoryL1Adapter**: Zstd/Zlib in-memory (*75% RAM reduction*)\n"
        "• **RedisL1Adapter**: Shared multi-process cluster caching\n"
        "• **Bloom Filter**: In-memory bit array for instant negative existence checks\n"
        "• **Auto-Rebuild**: Reconstructs filter to prevent bit saturation",
        size=11.5,
        color="#cbd5e1",
        line_spacing=6.0
    ))
    c1.add(ui.Spacer(height=10.0))
    b1_row = ui.Row(gap=10.0)
    b1_row.add(ui.Button("LRU Cache", background="#1e293b", size=11.0))
    b1_row.add(ui.Button("Zstd Compressed", background="rgba(56, 189, 248, 0.2)", size=11.0))
    c1.add(b1_row)
    c1.render(canvas, 40.0, 240.0)

    # COLUMN 2: Cryptographic Security Core (x=505, y=240, w=430)
    c2 = ui.Card(
        width=430.0,
        padding=22.0,
        corner_radius=16.0,
        background="#111722",
        border_color="rgba(168, 85, 247, 0.35)",
        shadow_blur=20.0,
        shadow_color="rgba(0, 0, 0, 0.4)"
    )
    c2.add(ui.Text("## [Security] Cryptographic Core", size=17.0, color="#c084fc"))
    c2.add(ui.Text("Galois/Counter Mode & Searchable Encryption", size=11.0, color="#94a3b8"))
    c2.add(ui.Divider(thickness=1.0, color="rgba(255, 255, 255, 0.08)", margin=6.0))

    c2.add(ui.Text(
        "• **AES-256-GCM & ChaCha20-Poly**: Authenticated AEAD ciphers\n"
        "• **PBKDF2-HMAC-SHA256**: 600,000-round human passphrase KDF\n"
        "• **HKDF Domain Separation**: RFC 5869 key isolation for index, data & integrity\n"
        "• **Blind Indexing**: Deterministic HMAC hashes enable fast exact queries\n"
        "• **Atomic Key Rotation**: Zero-downtime re-encryption with rollback safety",
        size=11.5,
        color="#cbd5e1",
        line_spacing=6.0
    ))
    c2.add(ui.Spacer(height=10.0))
    b2_row = ui.Row(gap=10.0)
    b2_row.add(ui.Button("AEAD Galois", background="#1e293b", size=11.0))
    b2_row.add(ui.Button("HKDF RFC 5869", background="rgba(168, 85, 247, 0.2)", size=11.0))
    c2.add(b2_row)
    c2.render(canvas, 505.0, 240.0)

    # COLUMN 3: Tier 2 - SQLite WAL Storage Engine (x=970, y=240, w=430)
    c3 = ui.Card(
        width=430.0,
        padding=22.0,
        corner_radius=16.0,
        background="#111722",
        border_color="rgba(34, 197, 94, 0.35)",
        shadow_blur=20.0,
        shadow_color="rgba(0, 0, 0, 0.4)"
    )
    c3.add(ui.Text("## [Tier 2] SQLite WAL Engine", size=17.0, color="#4ade80"))
    c3.add(ui.Text("High-concurrency Write-Ahead Logging & MMAP Direct I/O", size=11.0, color="#94a3b8"))
    c3.add(ui.Divider(thickness=1.0, color="rgba(255, 255, 255, 0.08)", margin=6.0))

    c3.add(ui.Text(
        "• **WAL Mode (Write-Ahead Log)**: Concurrent reads & writes without locks\n"
        "• **Direct Kernel MMAP**: 256 MB zero-copy memory-mapped I/O\n"
        "• **64 MB Page Cache**: Sub-millisecond B-Tree page traversal\n"
        "• **Composite Indexing**: `(expires_at, updated_at DESC)` optimizes glob search\n"
        "• **Optimistic Concurrency**: Version checks prevent lost updates across transactions",
        size=11.5,
        color="#cbd5e1",
        line_spacing=6.0
    ))
    c3.add(ui.Spacer(height=10.0))
    b3_row = ui.Row(gap=10.0)
    b3_row.add(ui.Button("WAL Mode", background="#1e293b", size=11.0))
    b3_row.add(ui.Button("MMAP 256MB", background="rgba(34, 197, 94, 0.2)", size=11.0))
    c3.add(b3_row)
    c3.render(canvas, 970.0, 240.0)

    # 6. Bottom Row: High-Throughput Engine, Integrity, Cloud Sync
    # Bottom Left: Asynchronous Write-Behind Batch Journal (x=40, y=595, w=660)
    b_left = ui.Card(
        width=660.0,
        padding=20.0,
        corner_radius=14.0,
        background="#10151f",
        border_color="rgba(245, 158, 11, 0.30)",
        shadow_blur=16.0,
        shadow_color="rgba(0, 0, 0, 0.3)"
    )
    b_left.add(ui.Text("### [Write-Behind] Journal & Native Async Engine", size=15.0, color="#fbbf24"))
    b_left.add(ui.Text(
        "• **In-Memory Batch Queue**: Coalesces writes, slashing SQLite transactions by **95%**\n"
        "• **322,580 writes/sec**: Flushes in atomic SQL batches with automatic version incrementing\n"
        "• **Full Async API**: `async_load_json`, `async_save_json`, `async_search` for FastAPI/Discord.py\n"
        "• **Synchronized Invalidation**: Guarantees zero zombie documents or desynchronized caches",
        size=11.5,
        color="#cbd5e1",
        line_spacing=5.0
    ))
    b_left.render(canvas, 40.0, 595.0)

    # Bottom Right: Zero-Knowledge Cloud Disaster Recovery (x=740, y=595, w=660)
    b_right = ui.Card(
        width=660.0,
        padding=20.0,
        corner_radius=14.0,
        background="#10151f",
        border_color="rgba(236, 72, 153, 0.30)",
        shadow_blur=16.0,
        shadow_color="rgba(0, 0, 0, 0.3)"
    )
    b_right.add(ui.Text("### [Disaster Recovery] Zero-Knowledge Cloud Sync", size=15.0, color="#f472b6"))
    b_right.add(ui.Text(
        "• **Online SQLite Backup API**: Non-blocking live database snapshots with zero downtime\n"
        "• **Whole-Snapshot Envelope Encryption**: AES-256-GCM envelope (`.db.enc`) before S3 upload\n"
        "• **Multi-Cloud Compatible**: Works with Cloudflare R2, AWS S3, Backblaze B2, and MinIO\n"
        "• **1-Command Disaster Recovery**: Automated remote download, integrity check, and atomic restore",
        size=11.5,
        color="#cbd5e1",
        line_spacing=5.0
    ))
    b_right.render(canvas, 740.0, 595.0)

    # 7. Flow Connectors / Data Pipelines (Subtle Lines with glowing nodes)
    # Connector between L1 -> Security Core
    canvas.draw_line(470.0, 360.0, 505.0, 360.0, stroke="#38bdf8", stroke_width=2.0)
    canvas.draw_circle(470.0, 360.0, 4.0, fill="#38bdf8")
    canvas.draw_circle(505.0, 360.0, 4.0, fill="#c084fc")

    # Connector between Security Core -> L2 SQLite
    canvas.draw_line(935.0, 360.0, 970.0, 360.0, stroke="#a855f7", stroke_width=2.0)
    canvas.draw_circle(935.0, 360.0, 4.0, fill="#c084fc")
    canvas.draw_circle(970.0, 360.0, 4.0, fill="#4ade80")

    # Connector down to Write-Behind and Cloud Sync
    canvas.draw_line(255.0, 545.0, 255.0, 595.0, stroke="#38bdf8", stroke_width=2.0)
    canvas.draw_line(1185.0, 545.0, 1185.0, 595.0, stroke="#4ade80", stroke_width=2.0)

    # 8. Footer Info
    canvas.draw_text("RENDERED WITH FEATHER ENGINE (PURE RUST VECTOR RASTERIZER • SIMD AVX2 • SUBPIXEL AA)", 40.0, 930.0, size=11.0, color="#64748b", font=font)
    canvas.draw_text("MIT LICENSE • REPOSITORY: Yannis-A-D/encrypted_sqlite_system", 1000.0, 930.0, size=11.0, color="#64748b", font=font)

    # Save to disk
    canvas.save(str(out_path))
    canvas.save(str(out_path_root))
    print(f"[Feather Engine] Generated Architecture Visual at: {out_path}")
    print(f"[Feather Engine] Generated Architecture Visual at: {out_path_root}")

if __name__ == "__main__":
    render_system_visual()
