import asyncio
import functools
import json
import time
import traceback
from typing import Any, Callable
from pydantic import BaseModel

from src.memory.store import log_action


def _serialize(obj: Any) -> str:
    """Helper to safely serialize function arguments or return values to a string."""
    if isinstance(obj, BaseModel):
        return obj.model_dump_json()
    if isinstance(obj, (dict, list, tuple, int, float, bool, type(None))):
        try:
            return json.dumps(obj, default=str)
        except Exception:
            return str(obj)
    return str(obj)


def log_call(func: Callable) -> Callable:
    """
    Decorator wrapping synchronous or asynchronous function calls.
    Writes input arguments, return value/error, status, and latency (ms) to `actions_log`.
    """
    func_name = getattr(func, "__qualname__", getattr(func, "__name__", "unknown_func"))

    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            inputs_str = _serialize({"args": args, "kwargs": kwargs})
            try:
                result = await func(*args, **kwargs)
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                outputs_str = _serialize(result)
                log_action(
                    func_name=func_name,
                    inputs=inputs_str,
                    outputs=outputs_str,
                    status="success",
                    latency_ms=latency_ms,
                )
                return result
            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                err_str = f"Exception: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                log_action(
                    func_name=func_name,
                    inputs=inputs_str,
                    outputs=err_str,
                    status="error",
                    latency_ms=latency_ms,
                )
                raise
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            inputs_str = _serialize({"args": args, "kwargs": kwargs})
            try:
                result = func(*args, **kwargs)
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                outputs_str = _serialize(result)
                log_action(
                    func_name=func_name,
                    inputs=inputs_str,
                    outputs=outputs_str,
                    status="success",
                    latency_ms=latency_ms,
                )
                return result
            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                err_str = f"Exception: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                log_action(
                    func_name=func_name,
                    inputs=inputs_str,
                    outputs=err_str,
                    status="error",
                    latency_ms=latency_ms,
                )
                raise
        return sync_wrapper
