## Server Structure

The files that are uploaded to the server follow this structure:

```
index.html
packages/
  |- [package_name]/
  |    |- cover.png
  |    |- meta.json
  |    |- [package_name].zip
  |- [another package]/...
  |...
```


## Metadata structure

```json
{
  "title": "The Hobbit",
  "author": "J. R. R. Tolkien",
  "edition": "??",
  "description": "In a hole, in the ground, there lived a hobbit."
  "files": {
    "audio": "audio.mp3",
    "transcript": "transcript.json",
    "cover": "cover.png"
  }
}
```

Metadata files are inherited from the parent directory, so any undefined field will be filled with what the meta of the parent directory contains.

> all fields contained in the "files" category can be ignored, here they are written as an example (and to show default values) but should usually be omitted. They are here if you want to override the default file structure.

The `part` field should contain the unique number of each part of a content. All meta files in the directory tree are read when the package is loaded, and the parts are ordered according to their part number.

