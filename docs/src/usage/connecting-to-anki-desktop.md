# Connecting Anki to the sync server

The [Djankiserv Connect](https://ankiweb.net/shared/info/1724518526) Anki addon is available in the Anki addons repository. You can choose to sync all of your Anki profiles or just some (or none) of them with this plugin, and it is the recommended way of pointing your Anki desktop to Djankiserv.

Remember to close and open Anki again for the addon to be visible after plugin installation!

When you have installed the addon (see Anki docs for installing addons), simply go to Tools -> Preferences -> Network, then fill in the required fields, namely check the "Use custom sync server" and put in the server address (e.g., http://localhost:8002/djs/ or what ever it is available under).

You may also configure Anki Desktop without the plugin.

Recent versions of `Anki` desktop (2.1.32+ and maybe a bit earlier) now require you to use an environment variable to configure the sync server endpoints if you want to use a custom server. For Windows you can do the following (`powershell`):

```
PS C:\Users\your.user> $env:SYNC_ENDPOINT_MEDIA='http://localhost:8002/djs/msync/'; $env:SYNC_ENDPOINT='https://localhost:8002/djs/sync/'; & "C:\Program Files\Anki\anki.exe"; Remove-Item Env:\SYNC_ENDPOINT_MEDIA; Remove-Item Env:\SYNC_ENDPOINT
```

On Linux (assuming `anki` is in your path, which it should be. This may also work on Mac?):

```
SYNC_ENDPOINT_MEDIA='http://localhost:8002/djs/msync/' SYNC_ENDPOINT='http://localhost:8002/djs/sync/' anki
```

For `Ankidroid` you need to go to Settings -> Advanced -> Custom Sync Server and fill in both of the server endpoints, namely the sync URL (e.g., http://localhost:8002/djs/) and msync URL (e.g., http://localhost:8002/djs/msync/), but remember that Ankidroid now requires SSL so you will need to either use the supplied Kubernetes Helm Chart or create certificates using some other mechanism!

## You may need to use a proxy

See [Installation / Working around chunking with a proxy](./installation.md#working-around-chunking-with-a-proxy).
