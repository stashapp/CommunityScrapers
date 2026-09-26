from pathlib import Path

import py_common.log as log
from py_common.deps import ensure_requirements

ensure_requirements("pyrate_limiter", "requests_ratelimiter")
from pyrate_limiter import SQLiteBucket
from requests_ratelimiter import LimiterSession

def get_limiter_session(**kwargs) -> LimiterSession:
    if not kwargs:
        kwargs = {"per_second": 1, "per_minute": 40}
        
    return LimiterSession(
        **kwargs,
        bucket_class=SQLiteBucket,
        bucket_kwargs={"path": str(Path(__file__).parent / "ratelimit.db")}
    )
