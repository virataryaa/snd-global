"""Draft saves: every Save in Edit mode is first committed as '<Dataset> draft | ...', which the revision log, revision dots and
history charts skip (they read only '<Dataset> | ...'). Publish folds every draft since the last published save into one
normal revision (first old value -> last new value per cell), so play-around saves never show up as history."""
import re

import streamlit as st

import ghstore as gh

_LINE = re.compile(r"^(.*): (.*) -> (.*)$")


def _pending(path, head):
    """Net change lines of the drafts saved after the last published save, oldest old -> newest new."""
    bodies = []
    for _ts, msg in gh.history(path):
        first, _, body = msg.partition("\n")
        if first.startswith(head + " draft |"):
            bodies.append(body)
        elif first.startswith(head + " |"):
            break
    net = {}
    for body in reversed(bodies):
        for ln in body.splitlines():
            m = _LINE.match(ln.strip())
            if m:
                k, old, new = m.groups()
                net[k] = (net[k][0] if k in net else old, new)
    return [f"{k}: {o} -> {n}" for k, (o, n) in net.items() if o != n]


def count(paths) -> int:
    """Cells changed by unpublished drafts. Also clears a draft flag left by a failed save."""
    st.session_state["_gh_draft"] = False
    if not gh.enabled():
        return 0
    try:
        return sum(len(_pending(p, h)) for p, h in paths)
    except Exception:
        return 0


def label(n, pend) -> str:
    parts = ([f"{n} unsaved"] if n else []) + ([f"{pend} pencilled in"] if pend else [])
    return " · ".join(parts)


def publish(paths, reason=""):
    """One normal revision per dataset with the net draft changes. The file content is untouched (a trailing newline flips)."""
    reason = " ".join(str(reason or "").split())[:140]
    done = 0
    for p, h in paths:
        lines = _pending(p, h)
        if not lines:
            continue
        msg = f"{h} | {len(lines)} change(s)" + (f" | reason: {reason}" if reason else "") + "\n\n" + "\n".join(lines)
        gh.commit(p, lambda t: (t[:-1] if t.endswith("\n\n") else t + "\n", None), msg)
        done += len(lines)
    for mod in ("snd", "brazil", "cocoa"):                     # revision dots / charts read the log
        try:
            __import__(mod).cell_history.clear()
        except Exception:
            pass
    return done
