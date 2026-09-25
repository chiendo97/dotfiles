# Design: Fetch thread starter message in `get` command

## Problem

When reading thread messages via `get --channel-id <thread-id>`, the thread starter message is missing. Discord threads created from a channel message store the starter in the parent channel, not in the thread's message list. This means the original context (often containing MR links, descriptions, or requests) is invisible.

## Solution

Modify the `get` command to detect when it's reading a thread and automatically prepend the starter message.

### Approach: Check channel type first

1. Call `GET /channels/{channel_id}` to get channel metadata
2. If channel type is a thread (10 = announcement_thread, 11 = public_thread, 12 = private_thread):
   - Thread ID = starter message ID
   - `parent_id` = parent channel ID
   - Fetch starter message via `GET /channels/{parent_id}/messages/{channel_id}`
   - Prepend it before the thread replies
3. Fetch thread messages normally as before
4. Display starter + thread messages in chronological order with visual separators

### Output format

```
--- thread starter ---
[2026-04-03 09:41:25] kwang1402 (msg:1489560215811653712)
  @Hoang Nguyen @Chien Le update to finance settlement posted date
  https://github.com/tex-corver/genbook-api/pull/332

--- thread replies ---
[2026-04-03 09:41:26] hoangi19 (msg:1489560451418161214)
  approved

--- 2 message(s) ---
```

### Error handling

If fetching the starter message fails (e.g. bot lacks permission on parent channel), silently skip it and show thread messages as before. No disruption to existing behavior.

### Scope

- Only the `get` command changes
- No new commands, models, or CLI options
- No changes to the skill doc (it already documents using thread ID as `--channel-id`)
- 1 extra API call per `get` invocation on threads (negligible)

### Thread type constants

```python
THREAD_TYPES = {10, 11, 12}  # announcement_thread, public_thread, private_thread
```
