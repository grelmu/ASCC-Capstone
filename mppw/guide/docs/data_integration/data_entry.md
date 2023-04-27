# Data Entry

For researchers working with smaller amounts of data, the Web UI of the MPPW is the primary way in which data is added to the warehouse.  There are three main ways data can be stored:

* Files in a file bucket artifact
* File artifacts attached to an operation
* Document artifacts and data frames attached to an operation

The primary goal of the warehouse is to allow the storage of *any* type of data, but for analysis it is useful to store information in a more specific location.  The overall philosophy is that, via scripts or later reclassification, the information in file buckets can be reworked into specific artifacts which can then be parsed for more specific information.  This can happen asynchronously, however, to keep a researcher's workflow as simple as possible.

## File buckets

TODO: Image

File buckets are the least specific storage - every operation is initialized, by default, with a file bucket for arbitrary file attachments.  These files can be of any size and can be organized into a nested directory.  Generally if there is no other place to record information, it can be added as a file.

## File artifacts

TODO: Image

File artifacts, classified in a particular operation as an artifact with a particular `kind_urn`, are more specific than files in file buckets in that the warehouse "knows" how they are related to the operation.  For example, the toolpath of a 3D print (`:fff` operation) is stored as a `:toolpath` `kind` artifact, which allows analysis scripts to search for all `:toolpath`s of 3D prints.

File artifacts do not contain data themselves, they are purely metadata and point at a file located at some URL.  By default, however, that URL points to the local operation's file bucket storage - this means a file uploaded as a `:toolpath`, for example, will *also* end up in the file bucket of the same `:fff` operation.  Remote URLs or URLs referencing other operations can also be specified.

## Document artifacts

TODO: Image

The next level of specificity is entering data as a (JSON) document in a form, specified by a [JSON schema](https://json-schema.org) as part of an artifact's schema.  A form is auto-generated from a `:document` artifact's JSON schema, and this allows the data entered to be placed in a JSON object with a well-known structure.  For example, dimensioning information for various ASTM standards can be placed in a `:document:named-dimensions` artifact, allowing analysis scripts to read the various measurements made of a specimen.  If stored in a file, analysis scripts would need to know how to parse the particular file formats, deal with parsing errors, etc.

### Frame artifacts

TODO: Image

A `:frame` artifact is an extension of a `:document`, and allows not only data entry of fields from a JSON schema but also an attached set of data in named columns.  Similar to a CSV, the columns allow repeated measurements over time (or some other dimension) to be naturally stored without needing to explicitly create and enter new JSON rows.  For example, `:frame:force-displacement` artifacts can be used to store measurements from mechanical tests with data copied directly from CSVs or spreadsheets. 