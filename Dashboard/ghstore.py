"""Tiny GitHub "database": read / write / history of files in the snd-global repo through the Contents API.

Used by the Entry page. Needs `github_token` in Streamlit Secrets (Contents: read and write on the repo).
One keep-alive session, the last sha of every file is remembered, so a save is a single PUT (re-read once on a conflict).
"""
import base64
from urllib.parse import quote

import requests
import streamlit as st

REPO = "virataryaa/snd-global"
BRANCH = "data"   # app data lives here: saves on this branch do not redeploy the app (it runs from main)


class GitHubError(Exception):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


def enabled() -> bool:
    try:
        return "github_token" in st.secrets
    except Exception:                                  # no secrets file at all (local run)
        return False


@st.cache_resource
def _session():
    s = requests.Session()
    tok = str(st.secrets["github_token"]).strip().strip('"').strip("'")
    s.headers.update({"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"})
    return s


@st.cache_resource
def _state() -> dict:
    """{path: {"text": ..., "sha": ...}} and {"history:<path>": [...]} - shared across reruns and sessions."""
    return {}


def _url(path: str) -> str:
    return f"https://api.github.com/repos/{REPO}/contents/{quote(path)}"   # quoted: the exports folder name has spaces


def _check(r):
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", "")
        except ValueError:
            msg = r.text[:200]
        hint = {401: "token is wrong or expired - re-paste github_token in Secrets",
                403: "token has no write access - give it Contents: Read and write on snd-global",
                404: "token cannot see the snd-global repo (or the file) - check the token",
                409: "file changed meanwhile - press Save again"}.get(r.status_code, "")
        raise GitHubError(f"GitHub {r.status_code}: {msg}. {hint}", r.status_code)


def cached_text(path: str):
    hit = _state().get(path)
    return hit["text"] if hit else None


def text_of(path: str, local) -> str:
    """Latest text of a data file: from the data branch when a token is set (kept in memory after the first read),
    else (or if GitHub fails) the local copy."""
    if enabled() and not _state().get(f"missing:{path}"):
        try:
            return cached_text(path) if cached_text(path) is not None else read(path)[0]
        except GitHubError as ex:
            if ex.status == 404:                                  # not on the data branch yet: stop asking until a save creates it
                _state()[f"missing:{path}"] = True
    with open(local, encoding="utf-8") as fh:
        return fh.read()


def read(path: str) -> tuple[str, str]:
    r = _session().get(_url(path), params={"ref": BRANCH}, timeout=20)
    _check(r)
    j = r.json()
    text = base64.b64decode(j["content"]).decode("utf-8")
    _state()[path] = {"text": text, "sha": j["sha"]}
    return text, j["sha"]


def commit(path: str, change, message: str, default=None):
    """change(text) -> (new_text, info). One PUT using the remembered sha; re-read once if the file moved on.
    Returns (new_text, info). Also puts the commit at the top of the remembered history.
    default: starting text when the file is not on the data branch yet (the first save creates it)."""
    st_ = _state()
    if path in st_:
        text, sha = st_[path]["text"], st_[path]["sha"]
    else:
        try:
            text, sha = read(path)
        except GitHubError as ex:
            if ex.status != 404 or default is None:
                raise
            text, sha = default, None
    new_text, info = change(text)
    for attempt in (0, 1):
        body = {"message": message, "branch": BRANCH, "content": base64.b64encode(new_text.encode("utf-8")).decode()}
        if sha:
            body["sha"] = sha
        try:
            r = _session().put(_url(path), json=body, timeout=20)
            _check(r)
            break
        except GitHubError as ex:
            if attempt == 0 and ex.status in (409, 422):           # someone else changed the file: re-read once
                text, sha = read(path)
                new_text, info = change(text)
                continue
            raise
    j = r.json()
    st_[path] = {"text": new_text, "sha": j["content"]["sha"]}
    st_.pop(f"missing:{path}", None)
    hist = st_.get(f"history:{path}")
    if hist is not None:
        hist.insert(0, (j["commit"]["committer"]["date"], message))
    return new_text, info


def history(path: str, n: int = 100) -> list[tuple[str, str]]:
    """[(iso time, full commit message)] newest first. Fetched once, new saves are added by commit()."""
    st_ = _state()
    key = f"history:{path}"
    if key not in st_:
        r = _session().get(f"https://api.github.com/repos/{REPO}/commits",
                           params={"path": path, "per_page": n, "sha": BRANCH}, timeout=20)
        _check(r)
        st_[key] = [(c["commit"]["committer"]["date"], c["commit"]["message"]) for c in r.json()]
    return st_[key]
