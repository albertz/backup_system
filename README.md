Distributed backup system
=========================

General idea: You have a bunch of systems and/or disks and a bunch of data and you want to keep copies / backups of your data on some of those systems/disks.

Structure
---------

I have grouped my data by those general types:

* Projects (coding or whatever)
* Pictures
* Movies
* Music
* …

For each type (i.e. in the specific associated directory, e.g. "Pictures"), there may be some own structure (Musics first level is music genre, then artist, etc.). And at the end, there are the entities (e.g. some project or some picture album).

A single entity is always handled as a single object; it cannot be separated. (To do that, you could just create 2 or more new entities, copy the stuff over there and delete the original entity. This may be so common that this may even be a basic operation.)

A database which keeps track over all existing entities. This database may be itself an entity in the whole system.


Basic operations
----------------

- create new project / base directory
- split an entity into several sub-entities. i.e. push the entity root-dir one down

