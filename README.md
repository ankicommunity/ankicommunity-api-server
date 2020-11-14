# djankiserv

`djankiserv` is an open source Django-based implementation of a synchronisation server for Anki 2.1+. It includes a user manager (the native Django user system).

[Installation](doc/Installation.md) - [Connecting Anki to the sync server](doc/ConnectingAnki.md) - [Development](doc/Development.md)

## About this implementation

This implementation was initially developed in order to support the spaced repetition functionality for [`Transcrobes`](https://transcrob.es), an open source language learning platform/ecosystem.

Any requests or functionality that don't interfere with using this project for that will definitely be entertained. Ideally the server would do everything that Ankiweb does, and much more. PRs are obviously always welcome!

### Technical differences

Unlike the other popular open source Anki synchronisation server [`anki-sync-server`](https://github.com/ankicommunity/anki-sync-server), `djankiserv` stores the user data in a "proper" RDBMS. There are two 'database connections' that can be set - those for the 'system' (sessions, users, etc.) and those for user data. The 'system' stuff is just plain old Django, so any supported database can be used. The user data part currently uses either `postgresql` schemas or `mysql` databases, and currently only supports those two, though supporting other RDBMSes will definitely be considered later. `sqlite3` is an embedded database and works great for that. It is not appropriate for use in modern web applications in the opinion of the maintainer, so will never be supported by `djankiserv`.

There is a basic API for getting certain, per-user collection-related information (decks, deck configuration, models, tags) and also `notes` for a given user. It may evolve to include other functions, statistics and even doing cards, though the focus is currently on getting and maintaining proper synchronisation as well as the basic API for `notes`.

### Limitations

This is alpha software with some occasional data loss bugs. It works, sorta, if you hold it right. If it kills your kittens then you were forewarned!

Current known limitations (bugs!):

- it doesn't support abort and if it crashes in the middle of a sync then the server will have a corrupt view of the database. You should force an upload sync on next synchronisation if this ever happens!
- The v2 scheduler is not supported, and it is unclear how difficult this might be to implement.
