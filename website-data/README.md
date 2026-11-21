# Dharma Tales Junior catalog sync

The public website is https://dharma-tales-junior.ableclay8.chatgpt.site .
Its reviewed static catalog is a fallback. Its live catalog is the public file
`website-data/catalog.json` on branch `main` in
`spiritualkidsvideos/dharmatalesjunior`. The website fetches this file on load
and every five minutes while open. Updating this data requires no Site deploy.

Use only public YouTube metadata and the existing GitHub app connection. Do not
enable billing, add a paid service, call credit-consuming vidIQ tools, change
repository visibility, or modify the private publisher repository.

## Run without the setup conversation

1. Use GitHub `fetch_file` with repository_full_name
   `spiritualkidsvideos/dharmatalesjunior`, ref `main`, and encoding `utf-8` for:
   - path `website-data/sync_catalog.py`
   - path `website-data/catalog.json`
   Use the returned complete UTF-8 `content` and retain the catalog's blob `sha`.
   The connection must permit reading these exact files and updating only the
   catalog. Do not print any credentials.
2. Write the fetched script and catalog in the current execution environment's
   scratch directory. Execute `python3 sync_catalog.py --catalog catalog.json`.
   It uses Python's standard library and the channel's public Atom feed:
   `https://www.youtube.com/feeds/videos.xml?channel_id=UCjq6Yf2kgwXbHvtNNY3K_WA`.
   It validates the channel and entries, merges new public uploads, updates
   titles, and preserves older videos that have aged out of the recent feed.
3. If fetching, parsing, or validation fails, leave the stored file unchanged
   and report the specific failure. Never replace it with an empty or partial
   feed. A recent feed alone cannot prove that an older video was deleted.
4. Use GitHub `update_file` on `website-data/catalog.json`, branch `main`,
   repository `spiritualkidsvideos/dharmatalesjunior`, with the complete updated
   UTF-8 JSON and the blob SHA retained in step 1. Suggested commit message:
   `Refresh public website video catalog`. No other path needs a write.
   If another writer changed it, refetch the current catalog and rerun the merge
   once. Never force-push, clear the file, or overwrite a conflict blindly.
5. Read the catalog back through GitHub `fetch_file`. Verify its channelId, checkedAt,
   video IDs, and count agree with the successful output. The anonymous URL is
   `https://raw.githubusercontent.com/spiritualkidsvideos/dharmatalesjunior/main/website-data/catalog.json`.
   Raw content can take several minutes to refresh in caches; a matching blob
   readback confirms persistence without writing a second time.

No publishing, metadata edits on YouTube, email, or paid APIs are authorized by
this sync. Return a concise count and result. Report failures clearly.

## Classification limits

The Atom feed contains recent public uploads, not a complete channel history.
The seed retains all 70 reviewed videos. New uploads are merged by video ID;
their title, thumbnail URL, publication time, and playback link appear
automatically. Known language, topic, and video type are preserved. New Hindi
titles are detected from Devanagari text or an explicit Hindi label. New Shorts
are identified by an explicit #Shorts label. The feed does not expose duration;
unclassified new uploads are labeled Video and remain visible under All videos
rather than being falsely labeled Full story. All syncs are additive; removal
of an older deleted/private video requires separate verification and cleanup.
