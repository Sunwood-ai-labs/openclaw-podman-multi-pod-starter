# Mattermost Tools

Heartbeat uses these entrypoints directly.

- `common_runtime.py`: shared Mattermost runtime helpers
- `get_state.py`: read current channel state and cooldown info
- `post_message.py`: post a message or thread reply
- `create_channel.py`: create or reuse a public channel
- `add_reaction.py`: add a reaction to a post

Legacy one-shot runners were removed so the folder only contains the current heartbeat helper path.
