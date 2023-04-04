import furl
import pydantic
import pymongo
import arrow
import datetime
from typing import List, Optional, Any, Union

from .. import OperationServices
from .. import ArtifactServices
from ... import models


class UnknownTimeSeriesSchemeException(Exception):
    pass


class UnknownTimeSeriesFieldException(Exception):
    pass


class TimeSeriesEvent(models.BaseJsonModel):

    """
    An event in time

    Consists of a "t" timestamp and an (optional) "ctx" (context) object
    with any event data.

    The datetime timestamp is, by default, stored in datetime format and
    serialized as an ISO datetime string.  Other timestamp formats such as
    numeric timestamps are possible and inferred if the time series has not
    been initialized with a standard timestamp field.  Mixing formats is
    not supported.
    """

    # Usually we should be datetime.datetime, but for compatibility with *any* time series we can
    # return any kind of sortable timestamp
    # DRAGONS: We include datetime.datetime for documentation purposes only, and *must* be listed last to
    # avoid auto-coercion
    t: Union[Any, datetime.datetime]
    ctx: Any

    @staticmethod
    def is_parseable(value):
        return "t" in value


class TimeSeriesStats(models.BaseJsonModel):

    """
    Information about storage of a time series artifact

    Consists of basic size and storage information, as well as any scheme-specific statistics.
    """

    size_bytes: int
    storage_url: str
    storage_stats: Any


class TimeSeriesServices(ArtifactServices):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scheme_backends = {}

        from .mongodb_time_series_services import MongoDbTimeSeriesServices

        mongodb_ts_services = MongoDbTimeSeriesServices(*args, **kwargs)

        self.scheme_backends["mongodb"] = mongodb_ts_services
        self.scheme_backends["mongodb+ts"] = mongodb_ts_services

    def init(self, artifact: models.DigitalArtifact, **kwargs):

        scheme = kwargs.get("scheme", "mongodb+ts")

        if scheme in self.scheme_backends:
            return self.scheme_backends[scheme].init(artifact, **kwargs)
        else:
            raise UnknownTimeSeriesSchemeException(
                f"Cannot initialize time series, unknown time series scheme '{scheme}'"
            )

    def stats(self, artifact: models.DigitalArtifact):

        """
        Returns the time series stats
        """

        series_furl = furl.furl(artifact.url_data)

        if series_furl.scheme in self.scheme_backends:
            return self.scheme_backends[series_furl.scheme].stats(artifact)
        else:
            raise UnknownTimeSeriesSchemeException(
                f"Cannot find stats of time series, unknown time series scheme in '{series_furl}'"
            )

    def get_bounds(self, artifact: models.DigitalArtifact):

        """
        Returns the time series min/max bounds
        """

        series_furl = furl.furl(artifact.url_data)

        if series_furl.scheme in self.scheme_backends:
            return self.scheme_backends[series_furl.scheme].get_bounds(artifact)
        else:
            raise UnknownTimeSeriesSchemeException(
                f"Cannot find bounds of time series, unknown time series scheme in '{series_furl}'"
            )

    def insert(self, artifact: models.DigitalArtifact, ts_events, **kwargs):

        """
        Inserts time series events into the stream
        """

        series_furl = furl.furl(artifact.url_data)

        if series_furl.scheme in self.scheme_backends:
            return self.scheme_backends[series_furl.scheme].insert(
                artifact, ts_events, **kwargs
            )
        else:
            raise UnknownTimeSeriesSchemeException(
                f"Cannot insert new events into time series, unknown time series scheme in '{series_furl}'"
            )

    def sample(
        self,
        artifact: models.DigitalArtifact,
        dt_bounds,
        limit=0,
        est_limit_bytes=0,
        inclusive_min=True,
        inclusive_max=True,
        **kwargs,
    ):

        series_furl = furl.furl(artifact.url_data)

        if series_furl.scheme in self.scheme_backends:
            return self.scheme_backends[series_furl.scheme].sample(
                artifact,
                dt_bounds,
                limit=limit,
                est_limit_bytes=est_limit_bytes,
                inclusive_min=inclusive_min,
                inclusive_max=inclusive_max,
                **kwargs,
            )
        else:
            raise UnknownTimeSeriesSchemeException(
                f"Cannot sample time series, unknown time series scheme in '{series_furl}'"
            )
