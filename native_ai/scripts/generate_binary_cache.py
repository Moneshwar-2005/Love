"""Script to generate and validate binary token caches for LOVE Native AI."""
import sys
import time
from pathlib import Path

# Add project root F:\LOVE to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from native_ai.data_cache.binary_cache import BinaryTokenCacheBuilder

def main():
    print("=" * 80)
    print("  LOVE NATIVE AI: BINARY TOKEN CACHE GENERATION (NAI-04)")
    print("=" * 80)

    builder = BinaryTokenCacheBuilder()
    print("1. Estimating cache storage and checking headroom...")
    est = builder.estimate_cache_storage()
    print(f"   Estimated Cache Size: {est['total_estimated_bytes'] / (1024**2):.2f} MB")
    print(f"   Drive Free Space:     {est['available_drive_free_bytes'] / (1024**3):.2f} GB")
    print(f"   Safe Headroom:        {est['safe_headroom_bytes'] / (1024**3):.2f} GB")
    print(f"   Headroom Safety:      {'PASSED' if est['is_safe'] else 'FAILED'}")

    if not est["is_safe"]:
        print("ERROR: Insufficient disk headroom. Aborting.")
        sys.exit(1)

    print("\n2. Building and verifying binary token caches...")
    manifest = builder.build_all_caches(force=True)

    print("\n" + "=" * 80)
    print("  CACHE GENERATION COMPLETE")
    print("=" * 80)
    print(f"Build Duration:   {manifest['build_duration_seconds']:.2f} seconds")
    print(f"Cache Status:     {manifest['status']}")
    print(f"Total Tokens:     {manifest['totals']['total_tokens_cached']:,}")
    print(f"Total Cache Size: {manifest['totals']['total_cache_bytes'] / (1024**2):.2f} MB")

    for split_name, s_info in manifest["splits"].items():
        toks = s_info["total_tokens"]
        docs = s_info["total_documents"]
        b_bytes = s_info["bin_bytes"]
        sha = s_info["bin_sha256"][:16] + "..."
        print(f"  [{split_name.upper()}] {toks:,} tokens | {docs:,} documents | {b_bytes:,} bytes | SHA: {sha}")

if __name__ == "__main__":
    main()
