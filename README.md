# Distributed backup system

General idea: You have a bunch of systems and/or disks and a bunch of data and you want to keep copies / backups of your data on some of those systems/disks.

In contrast to other backup solutions like [bup](https://github.com/bup/bup) or [Camliststore](http://camlistore.org/),
this backup system does not save the files seperately from your working copy.
This is an important distinction and is one of the main reason that this project exists.
This project is more like [git-annex](https://git-annex.branchable.com/). We will discuss the differences later.

The main idea is that you manage all or files as you normally would do, and this backup system keeps track of the changes of the *tree* of files and the file hashes.
Thus, it has some version control system, similar to Git, but the file contents themselves are not stored.
To actually backup some files, the backup system can clone your files, or parts of it.

Then, you might modify your files on different systems, and later want to merge your changes together. Thus, the change history is not simply linear, but can be a complex graph, like in Git.

This basic idea leads to two core functions:

* Versioning system.
This is used to store the meta-data, the directory tree, the file hashes, and similar stuff.
But not the file contents!
We need it to be detailed enough to do clever merges, and to detect all kinds of common modifications, like file/dir renames, etc.
We call this the versioned **backup index**.
* Sync / Clone.
You actually want to copy the file content, because you want to have a backup of it.
So, any sync or new clone of your data should handle both the version info, meta-data, etc., and the file contents.

(Paragraph for Git experts.)
With this goal, one possible approach might be to patch up Git directly that it simply does not store Git blobs.
When you do a new checkout of such repo, it will copy the files based on the existing files of the main repo.
However, this approach does not work, because we want to support partitioned copies, i.e. not every repo will have all existing dirs/files, probably even all repos.
Also, we want to store much more meta-data than Git does, e.g. permissions, other forms of hashes, and media related meta data.

When you rename some file/dir or modify some file, and you commit an update to the backup index, it should be able to automatically detect that modification, much like Git does. For doing this, we can support a very similar Git interface to `git commit`.

To follow the Git naming conventions, every clone/copy of the data (or parts of it) is called a **repository**.
Every repository will have its own copy of the full history of the backup index.
It does not need to have all meta-data nor the full copy of all files, only a subset of it.
It must know about the exact subset, to figure out deletions.

To support recovering from accidental deletions, we can use a tricky idea: For all existing files, the system will also create hardlinks. When you delete a file accidently, you can recover via the hardlink. When you commit a deletion, and you confirm the deletion in the commit, the system can remove the hardlink (or maybe alternatively after some number of commits, or some time delay, or only when running out of disk space).

To come back to git-annex: The basic design of git-annex covers much of what we want. It doesn't store the file contents itself, but it manages the content. And it is all based on Git.
However, for our purpose, it's too closely forced into the Git infrastructure by using also the Git CLI toolset.
E.g., it uses the same `.gitignore`, and it is itself a Git repository, living in a `.git` subdirectory.
Our backup system should be able to manage all files on the disk, which usually includes other Git repositories, and we don't want it to interpret those Git files as usual.
The logic can become more complex in some cases, e.g. it makes sense so save some auto-generated files, which you normally would not safe in a Git repository. We want that because 


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
* [bup](https://github.com/bup/bup)
* [git-annex](https://git-annex.branchable.com/)
* [unison](http://www.cis.upenn.edu/~bcpierce/unison/)
* [rsync](http://en.wikipedia.org/wiki/Rsync)
