# Output and Interaction Rules

Deterministic formatting rules - govern how output is presented, not what work gets
done. Apply on top of whatever the Risk Engine / role routing decided.

## 7-line rule

Any copyable content over 7 lines becomes a downloadable artifact file, never pasted
inline. Count lines first.

```python
def needs_artifact(content: str) -> bool:
    return content.count("\n") + 1 > 7
```

## Session-type formatting

| Session type | Format |
|---|---|
| Copy-paste (Termius, Shell In A Box) | Standard markdown code block, ready to paste directly. |
| Manual-typing (character by character, touch device) | Two-line format: human-readable line with explicit spacing, plus a plain code block with a copy button. Never combine a package name and its flags on one line in this mode. |

## Mobile-first requirement

Any script, prompt, or block of text meant for another system or person must:
1. Be delivered as a downloadable plain-text artifact file - one tap to select-all and
   copy on a touch device. Never paste long scripts inline.
2. Include the direct link/URL alongside it. Never make the recipient hunt for where it
   goes.

Both parts required together. Artifact without link, or link without artifact, fails
this rule.

## Human notification channel

ntfy is the mechanism, not Notion, for anything that needs to reach Nick in real time:
01's Band 1/2 escalation actions, 04's logged DA deadlocks, any Verifier failure on a
domain (08's Web Apps / UI) where a human eyeball is the fallback. Replaces Notion for
this purpose entirely, not an addition alongside it. Notion stays only for Claude Code
(cloud-hosted, not "truly local" - see 08's Software & AI Models policy).

```python
def notify_nick(message: str, urgency: str, topic: str) -> dict:
    """urgency in {'pause', 'inform'} maps to 01's Band 1 / Band 2 actions.
    topic is the ntfy topic - fixed per install, not chosen per-call. Fires exactly
    once per triggering event; no retry/spam on the same event."""
```

Band 1 blocks (LangGraph human-in-the-loop interrupt, see 00 Layer 4) until Nick acts;
Band 2 notifies and proceeds. Both fire through this same function - only difference is
whether the graph blocks afterward.

## VNC / screenshot as a verification artifact

For any Executor-Browser task (03; 08's Web Apps / UI domain), the captured VNC frame
or screenshot is itself an artifact under the 7-line rule - the Verifier and Nick both
need to see it, not be told it exists. Same two requirements as any other artifact:
1. Capture file itself, saved and referenced by path - never described in prose ("the
   page rendered correctly") as a substitute for the actual image.
2. Direct link/URL to it alongside whatever report references it.

Concrete form of 01's Detection axis for this domain: a completion claim with no linked
capture artifact is unverified, full stop, regardless of how confident the narrative
sounds. See 08's `verify_web_render_claim()`.

## Interleave pattern (input parsing, not output formatting)

When terminal output is pasted with `+plus-sign delimiters+` around inline commentary,
parse raw content as data and `+delimited+` text as the person's own commentary - do
not conflate the two. Governs how input is read, not how output is produced.

```python
def parse_interleaved(pasted_text: str) -> dict:
    """Splits on +...+ delimiters. Returns {'raw': [...], 'commentary': [...]}
    preserving order/position for both."""
```
