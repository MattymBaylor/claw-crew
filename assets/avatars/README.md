# Crew avatars (headshots)

Drop one image per agent here, named after the agent's **handle**:

```
assets/avatars/frank.png
assets/avatars/whatley.png
assets/avatars/mickey.png
assets/avatars/lloyd.png
assets/avatars/devola.png
assets/avatars/bania.png
assets/avatars/sueellen.png
assets/avatars/bookman.png
assets/avatars/steinbrenner.png
assets/avatars/uncle_leo.png
```

The roster points each agent at `assets/avatars/<handle>.png` by default
(override with an `avatar:` field on the agent in `config/roster.yaml`).

## Sizing specs (Slack app icon / bot headshot)

| Spec        | Value                                    |
|-------------|------------------------------------------|
| Shape       | **Square** (1:1)                         |
| Recommended | **512 × 512 px**                         |
| Minimum     | 512 × 512 px                             |
| Maximum     | 2000 × 2000 px                           |
| Format      | PNG or JPG (PNG preferred for crisp logos) |
| File size   | Keep under ~2 MB                         |
| Safe area   | Keep the face/subject centered; Slack may crop to a rounded square |

## How the picture actually gets onto the bot

Slack has **no public API to set a bot user's avatar**, so this is a one-time
manual step per app in the Slack app config:

1. https://api.slack.com/apps → pick the agent's app
2. **Basic Information → Display Information → App icon**
3. Upload the matching file from this folder, save.

Keeping the source images here means we have a versioned record and can
re-upload consistently if an app is ever recreated.
