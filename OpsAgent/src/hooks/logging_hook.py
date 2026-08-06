import asyncio
import functools
import json
import time
import traceback
from typing import Any, Callable
from pydantic import BaseModel

from src.memory.store import log_action


def _serialize(obj: Any, max_length: int = 2000) -> str:
    """Helper to safely serialize function arguments or return values to a string with length capping."""
    if isinstance(obj, BaseModel):
        res = obj.model_dump_json()
    elif isinstance(obj, (dict, list, tuple, int, float, bool, type(None))):
        try:
            res = json.dumps(obj, default=str)
        except Exception:
            res = str(obj)
    else:
        res = str(obj)

    if len(res) > max_length:
        return f"{res[:max_length]}... [truncated, total {len(res)} chars]"
    return res


def _record_action_log(
    func_name: str,
    inputs_str: str,
    start_time: float,
    result_or_err: Any,
    is_error: bool,
) -> None:
    """Helper recording function invocation metadata to actions_log database table."""
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    if is_error:
        outputs_str = f"Exception: {type(result_or_err).__name__}: {str(result_or_err)}\n{traceback.format_exc()}"
        status = "error"
    else:
        outputs_str = _serialize(result_or_err)
        status = "success"

    log_action(
        func_name=func_name,
        inputs=inputs_str,
        outputs=outputs_str,
        status=status,
        latency_ms=latency_ms,
    )


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
                _record_action_log(
                    func_name, inputs_str, start_time, result, is_error=False
                )
                return result
            except Exception as e:
                _record_action_log(func_name, inputs_str, start_time, e, is_error=True)
                raise

        return async_wrapper
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            inputs_str = _serialize({"args": args, "kwargs": kwargs})
            try:
                result = func(*args, **kwargs)
                _record_action_log(
                    func_name, inputs_str, start_time, result, is_error=False
                )
                return result
            except Exception as e:
                _record_action_log(func_name, inputs_str, start_time, e, is_error=True)
                raise

        return sync_wrapper
