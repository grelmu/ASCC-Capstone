from audioop import avg
import furl
import pydantic
import pymongo
import arrow
import datetime
from typing import List, Optional, Any
from .. import ArtifactServices
from ... import models


class UnkownTimeSeriesTypeException(Exception):
    pass


class UnkownTimeSeriesStorageStrategyException(Exception):
    pass


class UnknownTimeSeriesFieldException(Exception):
    pass


class UnknownTimeSeriesEncodingException(Exception):
    pass

class TimeSeriesServices(ArtifactServices):

    class TEvent(models.BaseJsonModel):

        """
        Time series consist of arbitrary event data at a particular time
        """

        t: datetime.datetime
        ctx: Any

    def sample(self, time_series_artifact: models.DigitalArtifact, t_bounds, limit, est_limit_bytes):

        series_furl = furl.furl(time_series_artifact.url_data)
        if series_furl.scheme in ["mongodb+ts", "mongodb", "mongodb+dbvox"]:
            return self.sample_mongodb_ts(time_series_artifact, t_bounds, limit, est_limit_bytes)
        else:
            raise UnkownTimeSeriesTypeException(
                f"Unkown time series type for {series_furl.url}"
            )

    def get_bounds(self, time_series_artifact: models.DigitalArtifact):
        """
        Returns the time series bounds based on "t_bounds" in a metadata document
        """

        if not time_series_artifact.url_data:
            raise UnkownTimeSeriesTypeException("No URL found for time series.")

        time_series_furl = furl.furl(time_series_artifact.url_data)
        if time_series_furl.scheme in ["mongodb+ts", "mongodb", "mongodb+dbvox"]:
            return self.get_mbd_bounds(time_series_artifact)
        else:
            raise UnkownTimeSeriesStorageStrategyException(
                f"Unkown time series type for {time_series_furl.url}"
            )

    def get_mdb_ts_collection(self, time_series_artifact):

        """
        Resolve the MDB collection of timed events from the artifact
        """

        time_series_furl = furl.furl(time_series_artifact.url_data)
        ts_furl = furl.furl(time_series_furl.url)
        base_furl = furl.furl(ts_furl)
        base_furl.scheme = "mongodb"
        base_furl.path = base_furl.path.segments[0]

        base_url = self.repo_layer.storage_layer.resolve_local_storage_url_host(
            base_furl.url
        )

        client = pymongo.MongoClient(base_url)
        return client[ts_furl.path.segments[0]][ts_furl.path.segments[1]]

    def get_mdb_collection_avg_doc_size(self, time_series_artifact, colname):
        """
        Get the average document size for the collection
        """
        time_series_furl = furl.furl(time_series_artifact.url_data)
        ts_furl = furl.furl(time_series_furl.url)
        base_furl = furl.furl(ts_furl)
        base_furl.scheme = "mongodb"
        base_furl.path = base_furl.path.segments[0]

        base_url = self.repo_layer.storage_layer.resolve_local_storage_url_host(
            base_furl.url
        )

        client = pymongo.MongoClient(base_url)
        return client[ts_furl.path.segments[0]].command("collstats",colname)["avgObjSize"]

    class DbTimeSeriesMeta(pydantic.BaseModel):
        t_bounds: Optional[list]
        dt_field: Optional[str] = "auto"
        dt_encoding: Optional[str]
        storage_strategy: Optional[str]
        storage_strategy_params: Any

    def get_mdb_ts_meta(self, collection, with_bounds=False):

        """
        Get existing metadata and do a bunch of work if it doesn't
        exist to infer the appropriate values.

        Generally this lets us be pretty loose about what we accept
        as time series, which is nice while we work out sensor data.
        """

        meta = collection.find_one({"_id": None})

        if meta is not None:
            meta = TimeSeriesServices.DbTimeSeriesMeta(**meta)
        else:
            meta = TimeSeriesServices.DbTimeSeriesMeta()

        # Infer dt fields if required
        if meta.dt_field is "auto" or meta.dt_encoding is None:

            example_doc = collection.find_one(
                {"_id": {"$ne": None}}, sort=[("_id", pymongo.ASCENDING)]
            )

            if meta.dt_field is "auto":
                for test_field in ["stamp", "timestamp", "ts", "poststamp"]:
                    if test_field in example_doc:
                        meta.dt_field = test_field
                        break

            if meta.dt_field is "auto":
                raise UnknownTimeSeriesFieldException(f"Cannot infer datetime field")

            if meta.dt_encoding is None:

                if isinstance(example_doc[test_field], datetime.datetime):
                    meta.dt_encoding = "datetime"
                elif isinstance(example_doc[test_field], str):
                    meta.dt_encoding = "str"
                else:
                    # TODO: Allow millisecond / nanosecond timestamps?
                    raise UnknownTimeSeriesEncodingException(
                        f"Cannot infer unkown datetime type: {type(example_doc[test_field])}"
                    )

        # Get the first/last timestamps
        # TODO: Exclusive upper?
        if with_bounds and meta.t_bounds is None:

            first_ts = collection.find_one(
                {"_id": {"$ne": None}},
                {meta.dt_field: True},
                sort=[(meta.dt_field, pymongo.ASCENDING)],
            )

            last_ts = collection.find_one(
                {"_id": {"$ne": None}},
                {meta.dt_field: True},
                sort=[(meta.dt_field, pymongo.DESCENDING)],
            )

            if first_ts is None:
                meta.t_bounds = [None, None]
            else:
                meta.t_bounds = [arrow.get(first_ts[meta.dt_field]).datetime, arrow.get(last_ts[meta.dt_field]).datetime]

        return meta

    def get_mdb_ts_collection_meta(self, time_series_artifact, with_bounds=False):
        collection = self.get_mdb_ts_collection(time_series_artifact)
        meta = self.get_mdb_ts_meta(collection, with_bounds=with_bounds)
        return (collection, meta)

    @staticmethod
    def mdb_time_bounded_query(collection, meta, t_bounds):

        if meta.dt_encoding == "datetime":
            t_bounds = tuple(arrow.get(bound).datetime for bound in t_bounds)
        elif meta.dt_encoding == "str":
            t_bounds = tuple(str(arrow.get(bound)) for bound in t_bounds)
        else:
            UnknownTimeSeriesEncodingException(
                f"Cannot query unkown datetime type: {meta.dt_encoding}"
            )

        return {meta.dt_field: {"$gte": t_bounds[0], "$lte": t_bounds[-1]}, "_id": {"$ne": None}}

    def get_mbd_bounds(self, time_series_artifact: models.DigitalArtifact):
        _, meta = self.get_mdb_ts_collection_meta(time_series_artifact, with_bounds=True)
        return meta.t_bounds

    def sample_mongodb_ts(self, time_series_artifact: models.DigitalArtifact, t_bounds, limit, est_limit_bytes):

        collection, meta = self.get_mdb_ts_collection_meta(time_series_artifact)

        # Converted the desired limit of bytes to a limit of docs
        # byte limit works same as the doc count limit: 0 => no limit
        if(est_limit_bytes != 0):
            avg_size = self.get_mdb_collection_avg_doc_size(time_series_artifact, collection.name)

            # this insures we round up if est_limit_bytes/avg_size < 1, without this it would set the limit to 0, which is no limit
            # alternatively could use math.ceil()
            doc_limit_from_bytes = (est_limit_bytes // avg_size) + (est_limit_bytes % avg_size > 0) 
            
            # default limit == 0 means no limit to doc count in .find()
            if(limit == 0):
                limit = doc_limit_from_bytes
            else:
                limit = min(limit, doc_limit_from_bytes)

        t_query = TimeSeriesServices.mdb_time_bounded_query(collection, meta, t_bounds)

        docs = collection.find(t_query,limit=limit)
        for doc in docs:
            # We've gotta wrap results in some standard format so the consumer can know
            # what time the event is at
            yield TimeSeriesServices.TEvent(t=arrow.get(doc[meta.dt_field]).datetime, ctx=doc)
