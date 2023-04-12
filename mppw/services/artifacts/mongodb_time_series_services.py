import furl
import pydantic
import json_stream
import arrow
import datetime
from typing import List, Optional, Any, Tuple, ClassVar

from .. import OperationServices
from .. import ArtifactServices
from ... import models

from .digital_time_series_services import TimeSeriesEvent, TimeSeriesStats

from .digital_point_cloud_services import PointCloudServices

import pymongo
import pymongo.errors
import pymongo.collection


class MongoDbTimeSeriesParams(models.BaseJsonModel):

    INFERRED_DT_FIELD_NAMES: ClassVar = ["stamp", "timestamp", "ts", "poststamp"]

    dt_field: Optional[str]
    dt_encoding: Optional[str]

    @property
    def has_dt_field(self):
        return (self.dt_field is not None) and (self.dt_field != "auto")

    @property
    def has_dt_encoding(self):
        return self.dt_encoding is not None

    @staticmethod
    def split_url_params(url):
        split_furl = furl.furl(url)
        params = MongoDbTimeSeriesParams(**(split_furl.query.params))
        for field_name in params.__fields__.keys():
            if field_name in split_furl.query.params:
                del split_furl.query.params[field_name]
        return (split_furl.url, params)

    @staticmethod
    def add_params_to_url(url, params):
        add_furl = furl.furl(url)
        add_furl.query.params.update(params.dict())
        return add_furl.url


class MongoDbTimeSeriesServices(ArtifactServices):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(
        self,
        artifact: models.DigitalArtifact,
        parent_mongodb_url=None,
        parent_operation_id=None,
        **kwargs,
    ):

        if not artifact.url_data and not parent_mongodb_url:

            parent_operation: models.Operation = (
                self.operation_parent(artifact)
                if not parent_operation_id
                else self.repo_layer.operations.query_one(id=parent_operation_id)
            )

            if parent_operation is None:
                raise Exception(
                    "Cannot initialize time series (mongodb+ts), no parent operation found for storage"
                )

            for process_data_node in parent_operation.attachments.find_nodes_by_path(
                OperationServices.PROCESS_DATA_KIND_PATH
            ):
                process_data_node: models.AttachmentGraph.AttachmentNode

                process_data_artifact: models.Artifact = (
                    self.repo_layer.artifacts.query_one(
                        id=process_data_node.artifact_id
                    )
                )

                if not isinstance(process_data_artifact, models.DigitalArtifact):
                    continue

                process_data_scheme = furl.furl(process_data_artifact.url_data).scheme
                if process_data_scheme not in ["mongodb"]:
                    continue

                parent_mongodb_url = process_data_artifact.url_data
                break

            if not parent_mongodb_url:
                raise Exception(
                    "Cannot initialize point cloud, no compatible operation process data found for storage"
                )

        return self.init_ts_collection(artifact, parent_mongodb_url, **kwargs)

    def stats(self, artifact: models.DigitalArtifact):

        ts_url, _ = MongoDbTimeSeriesParams.split_url_params(artifact.url_data)
        storage_furl = furl.furl(ts_url)
        storage_furl.scheme = "mongodb"

        ts_collection, params = self.get_ts_collection_and_params(artifact)
        collstats = self._get_ts_collection_collstats(ts_collection)
        storage_stats = {}
        storage_stats["params"] = params.dict()
        storage_stats["collstats"] = dict(
            (k, collstats[k]) for k in ["count", "avgObjSize", "nindexes"]
        )

        return TimeSeriesStats(
            size_bytes=collstats["size"],
            storage_url=storage_furl.url,
            storage_stats=storage_stats,
        )

    def get_bounds(self, artifact: models.DigitalArtifact):

        ts_collection, params = self.get_ts_collection_and_params(artifact)

        if not params.has_dt_field:
            # We don't have any docs to infer the field name from
            return None

        ts_doc_query = {"_id": {"$ne": None}, params.dt_field: {"$exists": True}}

        earliest_doc = ts_collection.find_one(
            ts_doc_query,
            {params.dt_field: True},
            sort=[(params.dt_field, pymongo.ASCENDING)],
        )

        # We don't have any docs even with an explicit field name
        if earliest_doc is None:
            return None

        latest_doc = ts_collection.find_one(
            ts_doc_query,
            {params.dt_field: True},
            sort=[(params.dt_field, pymongo.DESCENDING)],
        )

        return [
            self._encode_dt_value(params, earliest_doc[params.dt_field]),
            self._encode_dt_value(params, latest_doc[params.dt_field]),
        ]

    def insert(
        self, artifact: models.DigitalArtifact, ts_events, max_batch_size=1000, **_
    ):

        dbvox_collection, params = self.get_ts_collection_and_params(artifact)

        insert_ts = arrow.get().datetime
        next_batch = []

        def write_batch():
            dbvox_collection.insert_many(next_batch)
            next_batch.clear()

        for ts_doc in ts_events:

            #
            # Here we allow *either* TimeSeriesEvents or just docs with fields
            #

            if TimeSeriesEvent.is_parseable(ts_doc):
                if not params.has_dt_field:
                    params.dt_field = self._infer_ts_event_dt_field(ts_doc)
                ts_doc.setdefault("ctx", {})
                ts_doc["ctx"][params.dt_field] = ts_doc["t"]
                ts_doc = ts_doc["ctx"]
            else:
                if not params.has_dt_field:
                    params.dt_field = self._infer_dt_field(ts_doc)

            if not params.has_dt_field:
                params.dt_field = MongoDbTimeSeriesParams.INFERRED_DT_FIELD_NAMES[0]

            if not params.has_dt_encoding:
                # DRAGONS: If we don't explicitly give an encoding type,
                # force UTC datetimes - users can do weird stuff but they'll
                # need to be explicit about it
                params.dt_encoding = datetime.datetime.__name__

            if params.dt_field not in ts_doc:
                ts_doc[params.dt_field] = insert_ts

            ts_doc[params.dt_field] = self._encode_dt_value(
                params, ts_doc[params.dt_field]
            )

            next_batch.append(ts_doc)
            if max_batch_size not in [0] and len(next_batch) >= max_batch_size:
                write_batch()

        if next_batch:
            write_batch()

    def sample(
        self,
        artifact: models.DigitalArtifact,
        dt_bounds,
        limit=0,
        est_limit_bytes=0,
        inclusive_min=True,
        inclusive_max=True,
        **_,
    ):

        ts_collection, params = self.get_ts_collection_and_params(artifact)

        # Converted the desired limit of bytes to a limit of docs
        # byte limit works same as the doc count limit: 0 => no limit
        if est_limit_bytes > 0:
            avg_size_bytes = self._get_ts_collection_collstats(ts_collection)[
                "avgObjSize"
            ]

            # this insures we round up if est_limit_bytes/avg_size < 1, without this it would set the limit to 0, which is no limit
            # alternatively could use math.ceil()
            doc_limit_from_bytes = (est_limit_bytes // avg_size_bytes) + (
                est_limit_bytes % avg_size_bytes > 0
            )

            # default limit == 0 means no limit to doc count in .find()
            if limit == 0:
                limit = doc_limit_from_bytes
            else:
                limit = min(limit, doc_limit_from_bytes)

        dt_query = {
            "_id": {"$ne": None},
            params.dt_field: {
                f"$gt{'e' if inclusive_min else ''}": self._encode_dt_value(
                    params, dt_bounds[0]
                ),
                f"$lt{'e' if inclusive_max else ''}": self._encode_dt_value(
                    params, dt_bounds[1]
                ),
            },
        }

        ts_docs = ts_collection.find(dt_query, limit=limit)
        for ts_doc in ts_docs:
            # We've gotta wrap results in some standard format so the consumer can know
            # what time the event is at
            yield TimeSeriesEvent(
                t=self._encode_dt_value(params, ts_doc[params.dt_field]),
                ctx=ts_doc,
            )

    def init_ts_collection(
        self,
        artifact: models.DigitalArtifact,
        parent_mongodb_url: str,
        build_indexes=True,
        **params_kwargs,
    ):
        if not artifact.url_data:
            artifact.url_data = self._build_ts_collection_url(
                artifact, parent_mongodb_url, **params_kwargs
            )

        if build_indexes:
            self._build_ts_collection_indices(artifact)

        self.repo_layer.artifacts.update(artifact)
        return artifact

    def _build_ts_collection_url(
        self, artifact: models.DigitalArtifact, mongodb_url: str, **params_kwargs
    ):
        artifact_furl = furl.furl(mongodb_url)
        artifact_furl.scheme = "mongodb+ts"
        artifact_furl.path.segments.append(f"_artcoll-{str(artifact.id)}")

        params = MongoDbTimeSeriesParams(**params_kwargs)
        return MongoDbTimeSeriesParams.add_params_to_url(artifact_furl.url, params)

    def _build_ts_collection_indices(
        self,
        artifact: models.DigitalArtifact,
    ):
        ts_collection, params = self.get_ts_collection_and_params(artifact)

        dt_field_names = (
            [params.dt_field]
            if params.has_dt_field
            else MongoDbTimeSeriesParams.INFERRED_DT_FIELD_NAMES
        )

        for dt_field_name in dt_field_names:
            ts_collection.create_index(
                [
                    (dt_field_name, pymongo.ASCENDING),
                ],
                sparse=True,
            )

    def get_ts_collection_and_params(
        self, artifact: models.DigitalArtifact
    ) -> Tuple[pymongo.collection.Collection, MongoDbTimeSeriesParams]:

        """
        Resolve the MDB collection of timed events from the artifact
        """

        ts_url, params = MongoDbTimeSeriesParams.split_url_params(artifact.url_data)
        client_furl = furl.furl(ts_url)
        client_furl.scheme = "mongodb"
        client_furl.path = client_furl.path.segments[0]

        client_url = self.repo_layer.storage_layer.resolve_local_storage_url_host(
            client_furl.url
        )

        client = pymongo.MongoClient(client_url)
        ts_furl = furl.furl(ts_url)
        ts_collection = client[ts_furl.path.segments[0]][ts_furl.path.segments[1]]

        legacy_params = ts_collection.find_one({"_id": None})
        if legacy_params:
            params = MongoDbTimeSeriesParams(**legacy_params)

        if (not params.has_dt_field) or (not params.has_dt_encoding):

            example_ts_doc_query = {"_id": {"$ne": None}}
            if params.has_dt_field:
                example_ts_doc_query[params.dt_field] = {"$exists": True}
            example_ts_doc = ts_collection.find_one(
                example_ts_doc_query, sort=[("_id", pymongo.ASCENDING)]
            )

            if example_ts_doc is not None:

                if not params.has_dt_field:
                    params.dt_field = self._infer_dt_field(example_ts_doc)

                if params.dt_field in example_ts_doc and not params.has_dt_encoding:
                    params.dt_encoding = self._infer_dt_encoding(
                        example_ts_doc[params.dt_field]
                    )

        return (ts_collection, params)

    def _infer_dt_field(self, ts_doc):
        for field_name in MongoDbTimeSeriesParams.INFERRED_DT_FIELD_NAMES:
            if field_name in ts_doc:
                return field_name
        return None

    def _infer_ts_event_dt_field(ts_event):
        if "ctx" in ts_event:
            for field_name in MongoDbTimeSeriesParams.INFERRED_DT_FIELD_NAMES:
                if (
                    field_name in ts_event["ctx"]
                    and ts_event["t"] == ts_event["ctx"][field_name]
                ):
                    return field_name
        # Default to the preferred field name since this event gets rewritten
        return MongoDbTimeSeriesParams.INFERRED_DT_FIELD_NAMES[0]

    def _infer_dt_encoding(self, dt_value):
        # Be slightly paranoid about datetime/str subclasses
        if isinstance(dt_value, datetime.datetime):
            return datetime.datetime.__name__
        elif isinstance(dt_value, str):
            try:
                arrow.get(dt_value)
                return datetime.datetime.__name__ + str.__name__
            except arrow.parser.ParserError:
                return str.__name__
        else:
            return type(dt_value).__name__

    def _encode_dt_value(
        self,
        params: MongoDbTimeSeriesParams,
        dt_value,
    ):
        if params.dt_encoding == datetime.datetime.__name__:
            return arrow.get(dt_value).to("utc").datetime
        elif params.dt_encoding == datetime.datetime.__name__ + str.__name__:
            return str(arrow.get(dt_value).to("utc"))
        else:
            return dt_value

    def _get_ts_collection_collstats(
        self, ts_collection: pymongo.collection.Collection
    ):
        ts_db = ts_collection.database
        return ts_db.command("collstats", ts_collection.name)
