"""Aggregate metrics only. Never capture requests, responses or exception payloads."""
import functools
import os
import time


def observed(function):
    @functools.wraps(function)
    def wrapped(event, context):
        if not os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            return function(event, context)
        from aws_lambda_powertools import Metrics, Tracer
        from aws_lambda_powertools.metrics import MetricUnit
        service = os.environ.get('POWERTOOLS_SERVICE_NAME', 'airguardian')
        metrics = Metrics(namespace='AirGuardian', service=service)
        tracer = Tracer(service=service, auto_patch=False)
        traced = tracer.capture_lambda_handler(capture_response=False, capture_error=False)(function)
        started = time.monotonic()
        try:
            result = traced(event, context)
            if isinstance(result, dict) and result.get('batchItemFailures'):
                metrics.add_metric('DeliveryOrServiceFailures', MetricUnit.Count, len(result['batchItemFailures']))
            if isinstance(result, dict) and result.get('statusCode', 200) >= 500:
                metrics.add_metric('DeliveryOrServiceFailures', MetricUnit.Count, 1)
            if isinstance(result, dict) and result.get('statusCode') == 200 and event.get('rawPath', '').endswith('/announce'):
                metrics.add_metric('PlansPublished', MetricUnit.Count, 1)
            return result
        except Exception:
            metrics.add_metric('DeliveryOrServiceFailures', MetricUnit.Count, 1)
            raise
        finally:
            metrics.add_metric('Latency', MetricUnit.Milliseconds, (time.monotonic()-started)*1000)
            metrics.flush_metrics()
    return wrapped


def stale_metric():
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        from aws_lambda_powertools import Metrics
        from aws_lambda_powertools.metrics import MetricUnit
        metrics = Metrics(namespace='AirGuardian', service=os.environ.get('POWERTOOLS_SERVICE_NAME', 'airguardian'))
        metrics.add_metric('StaleSourceCount', MetricUnit.Count, 1)
        metrics.flush_metrics()
