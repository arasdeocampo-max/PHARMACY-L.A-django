from .models import AuditEvent


def record_audit(actor, action, target="", detail=""):
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        target=str(target),
        detail=detail,
    )