from prometheus_client import Counter

REQUEST_COUNT = Counter("app_request_count", "Total request count")

def setup_metrics(app):
    @app.middleware("http")
    async def count_requests(request, call_next):
        REQUEST_COUNT.inc()
        return await call_next(request)
