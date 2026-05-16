from ninja import Router

from .schemas import (
    AdminAgentStatusSchema,
    AdminSupportMessageCreateSchema,
    AdminSupportThreadCreateSchema,
)
from .services import AdminAgentError, AdminAgentService

router = Router(tags=["RepireCRM Admin"])


def _ensure_admin_agent_access(request):
    user = request.auth
    if user.is_superuser or user.is_director:
        return
    if user.has_permission("settings.view_shop_settings"):
        return
    raise PermissionError("Нет прав для управления центральной админкой")


def _admin_service(request) -> AdminAgentService:
    _ensure_admin_agent_access(request)
    return AdminAgentService()


@router.get("/status", response=AdminAgentStatusSchema)
def get_admin_agent_status(request):
    return _admin_service(request).status_snapshot()


@router.post("/heartbeat", response=dict)
def send_admin_agent_heartbeat(request):
    return _admin_service(request).send_heartbeat(force=True)


@router.get("/support/threads", response={200: list[dict], 502: dict})
def list_admin_support_threads(request):
    try:
        return _admin_service(request).list_support_threads()
    except AdminAgentError as exc:
        return 502, {"error": str(exc)}


@router.post("/support/threads", response={201: dict, 502: dict})
def create_admin_support_thread(request, payload: AdminSupportThreadCreateSchema):
    try:
        return 201, _admin_service(request).create_support_thread(
            subject=payload.subject,
            priority=payload.priority,
            body=payload.body,
            author_name=payload.author_name or request.auth.full_name,
        )
    except AdminAgentError as exc:
        return 502, {"error": str(exc)}


@router.get(
    "/support/threads/{thread_id}/messages", response={200: list[dict], 502: dict}
)
def list_admin_support_messages(request, thread_id: int):
    try:
        return _admin_service(request).list_support_messages(thread_id)
    except AdminAgentError as exc:
        return 502, {"error": str(exc)}


@router.post("/support/threads/{thread_id}/messages", response={201: dict, 502: dict})
def reply_admin_support_thread(
    request, thread_id: int, payload: AdminSupportMessageCreateSchema
):
    try:
        return 201, _admin_service(request).reply_support_thread(
            thread_id=thread_id,
            body=payload.body,
            author_name=payload.author_name or request.auth.full_name,
        )
    except AdminAgentError as exc:
        return 502, {"error": str(exc)}
