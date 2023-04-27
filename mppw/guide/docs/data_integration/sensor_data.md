# Sensor Data

A major focus of the MPPW is to store data from manufacturing processes, and usually these processes are instrumented with a variety of sensors. There are a number of ways to integrate sensor data with the data warehouse, in rough order of simplicity and automation:

- Manual upload of data post-process
- Local-to-warehouse database sync
- Upload via data warehouse APIs

All forms of data entry are currently supported, but using the warehouse APIs for automated data storage is the primary target.

> Sensor data integration is currently an area of active development.

## Sensor Data Workflow

Generally any workflow using the data warehouse to capture sensor data proceeds as follows:

1. Create a new operation of the appropriate type in the data warehouse
1. Forward the initialized operation process data database bucket *or* operation id (preferred) to the sensor data collection platform
1. As an operation proceeds, use the provided database or initialized time series and point clouds (preferred) to store data in the warehouse.  Note that storing data as time series and point clouds will allow dynamic monitoring of the loaded data
1. After the operation completes, refine and analyze the stored data from the warehouse

Generally the major interaction between the warehouse and a sensor platform is in the second step - details of this will depend on the specific sensor platform in use.

> There is prototype integration with a UMaine "OP UI" system currently built into the data warehouse.

## Process data and database buckets

All operations, by default, are initialized with a `:database-bucket` artifact to store arbitrary process data. Similar to the `:file-bucket`, database buckets are essentially untyped collections of data at some database URL (currently only MongoDB is supported). Analysis scripts can access this data but there is no guarantee of format or content. Each operation-specific bucket has operation-specific auto-generated read-only and read-write credentials.

TODO: Image

Similar to the `:file-buckets` described in [data entry](./data_entry.md), `:database-buckets` are the default backing storage to other, more specific, data artifacts. As described below, `:time-series` and `:point-clouds` are initialized (again, by default) as references to collections in the local `:database-bucket`.

> Supporting a wider range of database bucket storage is an area of active development.

### Manual or automatic database sync

Via the web UI, the URL of a database bucket can be used to manually sync or load data from another data source. This is logically similar to manual file uploads, just in a different format.

## Time-series APIs

More specific than a general "collection" of data, a `:time-series` artifact can be created and attached to an operation. These `:time-series` artifacts, indicated by the name, support queries over time ranges for _events_ of arbitrary format. Usually sensor data collected over time naturally forms a `:time-series` artifact.

Time series artifacts directly store only a URL pointing to some collection of data supporting time range queries. Currently, only indexed MongoDB collections are supported. By default, when initialized, a time series artifact will create an indexed collection in the local operation's database bucket, which allows any amount of time series data to be stored in an operation.

> Supporting a wider range of time series storage is an area of active development.

Time series have a set of dedicated APIs wrapping the data entry and query:

- `../services/time-series/init` - As mentioned above, initializes the storage of a time series, which, by default, points to a new collection in the local operation's database bucket.
- `../services/time-series/insert` - Inserts (many) new time series events into a time series artifact.
- `../services/time-series/sample` - Queries a time series artifact based on date/time range.

Note that when using the time-series APIs, the data source can remain ignorant about details of data storage, making this the most flexible storage option.

See the [API Documentation](/docs) for more detailed information on using the time-series APIs.

### Image events

Sensors that produce image frames (as part of a video stream or otherwise) can be stored in `:time-series` artifacts where each frame is an event. By convention, if the binary image data is encoded in `.tiff`, `.jpeg`, or `.png` format and base-64 encoded in a JSON string, it can be displayed, interpreted, and downloaded by the MPPW web UI if the image data is in a field named:

- `image_[tiff|jpeg|png]_b64`

## Point cloud APIs

As an extension of time series artifacts, `:point-cloud` artifacts support storing events not only in time but in space - here called `points`. These `:point-cloud` artifacts, support queries over space and time ranges and can also include other data of arbitrary format. Registered sensor data often naturally forms a `:point-cloud` artifact.

Again, similar to time series artifact, point cloud artifacts directly store only a URL pointing to some collection of data supporting spacetime queries. (Currently, only MongoDB collections using dbhash voxel addressing is supported.) By default, when initialized, a point cloud artifact will create an indexed collection in the local operation's database bucket, which allows any amount of points to be stored in an operation.

> Supporting a wider range of point cloud storage is an area of active development.

Point clouds have a set of dedicated APIs wrapping the data entry and query:

- `../services/point-cloud/init` - Initializes the storage of a point cloud, which, by default, points to a new collection in the local operation's database bucket.
- `../services/point-cloud/insert` - Inserts (many) new points into a point cloud artifact.
- `../services/point-cloud/points` - Queries a point cloud artifact based on spacetime ranges.

Note that when using the point-cloud APIs, the data source can remain ignorant about details of data storage, making this the most flexible storage option.

See the [API Documentation](/docs) for more detailed information on using the point-cloud APIs.
