"""
In-process bridge into GeoNode's real upload/import pipeline
(``geonode.upload`` — the former standalone "geonode-importer" app, folded
into GeoNode core as of this instance's version).

Why in-process and not REST: this runs from a management command already
executing as a trusted Django process on the same box, with a real ``user``
object in hand — going out over HTTP would mean re-solving auth for no
benefit. This reproduces exactly what
``geonode.upload.api.views.ImporterViewSet.create()`` does, minus the
DRF/HTTP/StorageManager-clone layer (the file is already a real local path,
so there's nothing to clone).

The import itself is asynchronous (Celery-backed) even called this way —
each internal pipeline step re-queues the next step via ``apply_async()``
onto the real Celery broker, so a live celery worker is required. This
module only starts the chain and gives you a way to poll it to completion;
it does not itself run synchronously.
"""

import time

from geonode.upload.celery_tasks import import_orchestrator
from geonode.upload.orchestrator import orchestrator
from geonode.upload.models import ResourceHandlerInfo
from geonode.resource.models import ExecutionRequest


class ImportFailed(Exception):
    pass


class ImportTimedOut(Exception):
    pass


def start_import(file_path, owner, action="upload", title=None):
    """
    Kick off a real GeoNode import for a local file already on disk
    (visible from both the django and celery containers — e.g. under a
    shared volume such as /tmp or /data).

    Returns the execution_id (UUID) to hand to wait_for_import().
    Raises ImportFailed immediately if no handler in the registry can
    accept this file/action combination (e.g. unrecognized extension).
    """
    _data = {"base_file": file_path, "action": action}

    handler = orchestrator.get_handler(_data)
    if handler is None or not handler.can_do(action):
        raise ImportFailed(f"No importer handler can handle {file_path!r} for action {action!r}")

    extracted_params, remaining_data = handler.extract_params_from_data(_data, action=action)
    handler_path = str(handler)

    input_params = {
        "files": remaining_data,
        "handler_module_path": handler_path,
        "temporary_files": remaining_data,
        **extracted_params,
    }

    first_step = next(iter(handler.get_task_list(action=action)))

    execution_id = orchestrator.create_execution_request(
        user=owner,
        func_name=first_step,
        step=first_step,
        input_params=input_params,
        resource=extracted_params.get("resource_pk"),
        action=action,
        name=title,
    )

    import_orchestrator.s(
        remaining_data, str(execution_id), handler=handler_path, action=action, step=first_step
    ).apply_async()

    return execution_id


def wait_for_import(execution_id, timeout=300, poll_interval=2):
    """
    Poll the ExecutionRequest until the pipeline finishes, fails, or
    ``timeout`` seconds elapse. Returns the created ResourceBase (real
    subtype, e.g. Dataset) on success.

    Raises ImportFailed on a reported pipeline failure, ImportTimedOut if
    it never resolves in time (the execution keeps running server-side —
    it is NOT cancelled; a caller can poll again later with the same id).
    """
    deadline = time.monotonic() + timeout
    while True:
        execution = ExecutionRequest.objects.filter(exec_id=execution_id).first()
        if execution is None:
            raise ImportFailed(f"ExecutionRequest {execution_id} vanished while polling")

        status = execution.status
        if status == ExecutionRequest.STATUS_FAILED:
            raise ImportFailed(execution.log or f"execution {execution_id} failed with no log message")

        if status == ExecutionRequest.STATUS_FINISHED:
            info = ResourceHandlerInfo.objects.filter(execution_request=execution).first()
            if info is None or info.resource is None:
                raise ImportFailed(
                    f"execution {execution_id} finished but produced no ResourceHandlerInfo/resource"
                )
            return info.resource.get_real_instance()

        if time.monotonic() >= deadline:
            raise ImportTimedOut(
                f"execution {execution_id} still {status!r} after {timeout}s "
                "(it keeps running server-side; poll again later with the same id)"
            )

        time.sleep(poll_interval)


def import_and_wait(file_path, owner, action="upload", title=None, timeout=300, poll_interval=2):
    """Convenience wrapper: start_import() + wait_for_import() in one call."""
    execution_id = start_import(file_path, owner, action=action, title=title)
    return wait_for_import(execution_id, timeout=timeout, poll_interval=poll_interval)
