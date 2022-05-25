# MPPW Artifact and Operation Schemas

The MPPW data storage layer has very light schema requirements:

- Artifacts are entities which store data, either locally in a JSON object or remotely as a URL
- Operations are entities with a nested tree of artifact attachments

The information defining the structure of artifacts and operations lives at a higher level to allow it to be easily configurable. Adding a new artifact or operation type does not require editing the database structure, instead the definition lives as a file which can be changed and reloaded on restart. The goal is for it to be easy for researchers to create new artifacts and operations to define data collection for large or specialized experiments in manufacturing.

> NOTE Long-term, the goal is for these schemas to be stored in the database and to allow adding and removing schemas via the API.

Both kinds of schemas define the default names and descriptions of the artifacts and operations. The schemas themselves are written in JSON5 for more readable syntax, but any convenient representation could be used.

## Artifact Schemas

Artifact schemas define the data stored in the artifacts, when stored as a JSON object, as a [JSON schema](https://json-schema.org/).

> NOTE Long-term, other kinds of data definitions could be used alongside JSON schema and maybe also URL validations

## Operation Schemas

Operation schemas define two major data relations:

- The tree structure of attached artifacts (the data-entry view)
- The input/output relations between artifacts during the potentially-multiple steps of the operation (the provenance view)

Essentially the form-like tree is meant to provide a more work-instruction style list of data to collect, while the provenance view represents the data relationships that are not always well-captured by a list. For example, each of the parts after a :fff operation may be measured in various ways, and each of those measurements is a separate "step", but it's (arguably) more natural to just attach that data to the parts themselves.

Importantly, the tree (and implicitly the step) relationships are _named_, which means it's possible to distinguish different _kinds_ of inputs and output for each step.

Operation schemas can inherit artifact trees from multiple "parent" operation types, making it easy to add basic modifications to an existing operation or create families of operations.

> NOTE Long-term, consider a step-like view for data entry if easy enough to use

## Service Plugins

Schemas may also define more complex behavior via a _service class_. The service class is able to add functionality related to the artifact or operation (including creating and managing other artifacts or operations).

> NOTE Currently the service class is not able to add API endpoints, but that limitation may be removed
