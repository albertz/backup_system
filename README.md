# Distributed backup system

General idea: You have a bunch of systems and/or disks and a bunch of data and you want to keep copies / backups of your data on some of those systems/disks.

## Structure

I have grouped my data by those general types:

* Projects (coding or whatever)
* Pictures
* Movies
* Music
* …

(@az: also see `~/Documents/basis-einheiten.txt`. TODO: merge in here.)

For each type (i.e. in the specific associated directory, e.g. "Pictures"), there may be some own structure (Musics first level is music genre, then artist, etc.). And at the end, there are the entities (e.g. some project or some picture album).

A single entity is always handled as a single object; it cannot be separated. (To do that, you could just create 2 or more new entities, copy the stuff over there and delete the original entity. This may be so common that this may even be a basic operation.)

A database which keeps track over all existing entities. This database may be itself an entity in the whole system.


## Basic operations

- create new project / base directory
- split an entity into several sub-entities. i.e. push the entity root-dir one down


## Object types

- A directory. This is also versionized. It contains a list of other objects.
- A file. This is versionized.

Every object has one or more ids.


## Tool

Current status: Single line, updating (on console). E.g.: Currently indexing ...jpg. Or: Graphical status message, also updating itself to latest state.

## Different types of data

There is data on different levels, some of it mutable, some immutable, depending on the interpretation. I like to think about it as immutable blobs/objects like it Git, with unique ids (refs). However, depending on the interpretation, it is mutable, e.g. like the metadata.

Also, it is not obvious yet where to store certain data and how to categorize them and abstract it.

* The file content itself. Mutable, so a reference to it always points to the latest version? Or immutable, so a reference points always to the same data?
* The current metadata of the file. This is like the author, creation date and also permissions (maybe just use some light version of ACL?). For pictures, also info like what person is in the picture, etc.
* Persons / contacts.
* The history of some mutable object (metadata or file or whatever).

The metadata might also be available just as a normal file on the filesystem, e.g. like `${file}.metadata` or so.

In some cases, it is not obvious what the smallest entity is. E.g., some log or list of text comment entries or so, is it a single object or a list of multiple single objects? Some metadata such as comments, are they metadata or are they seperate data objects, maybe with their own metadata?

---

## Related projects

* [Camliststore](http://camlistore.org/) ([HackerNews](https://news.ycombinator.com/item?id=2156374)), "personal storage system for life", see also the [overview](http://camlistore.org/docs/overview)


