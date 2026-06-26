"""Runtime persistence backends that sit behind the unlocked autonomy seam (``core_state``).

These do NOT change the desi_layer9 kernel — they reuse its own ``snapshot.capture``/``restore`` and
``snapshot_hash``/``verify_chain`` and only swap the storage medium. The three-space store in the
parent package is a richer projection; this is the plain materialised backend that lets the loop
load without a full journal replay.
"""
