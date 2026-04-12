"""
Compliance guard tests – covers:
1. UI compliance guard (dialog before sensitive action)
2. Operator confirmation with audit log (who, when, action, request_id, reason)
3. API blocks action without compliance confirmation when enforcement is ON
4. COMPLIANCE_ENFORCEMENT toggle (dev mode vs prod enforcement)
"""

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import routes_compliance, routes_ingest, routes_query
from app.db.models import AuditLog
from app.services import compliance
from app.services.request_context import reset_request_id, set_request_id


# ---------------------------------------------------------------------------
# 1. Compliance guard – action blocked in enforcement mode (simulates UI guard)
# ---------------------------------------------------------------------------

class TestComplianceGuardBlocksWithoutConfirmation:
    """Sensitive actions must be rejected when enforcement is ON and no confirmation is provided."""

    def test_query_blocked_without_confirmation(self, monkeypatch, db_session):
        compliance.set_compliance_enforcement_override(True)
        user = SimpleNamespace(id=1, role="User")
        monkeypatch.setattr(routes_query, "answer_no_rag", lambda query, **kw: "x")

        try:
            with pytest.raises(HTTPException) as exc:
                routes_query.ask(
                    payload=routes_query.QueryRequest(query="test", mode="no-rag"),
                    user=user,
                    db=db_session,
                )
            assert exc.value.status_code == 422
            assert "Compliance confirmation is required" in exc.value.detail
        finally:
            compliance.set_compliance_enforcement_override(None)

    def test_ingest_blocked_without_confirmation(self, monkeypatch, db_session, source):
        compliance.set_compliance_enforcement_override(True)
        user = SimpleNamespace(id=1, role="Curator")
        monkeypatch.setattr(routes_ingest, "run_ingest", lambda **kw: {"status": "completed", "document_id": 1})

        try:
            with pytest.raises(HTTPException) as exc:
                routes_ingest.ingest_url(
                    payload=routes_ingest.IngestRequest(source_id=source.id, url=f"{source.base_url}/page"),
                    user=user,
                    db=db_session,
                )
            assert exc.value.status_code == 422
        finally:
            compliance.set_compliance_enforcement_override(None)

    def test_query_allowed_with_confirmation(self, monkeypatch, db_session):
        compliance.set_compliance_enforcement_override(True)
        user = SimpleNamespace(id=1, role="User")
        monkeypatch.setattr(routes_query, "answer_no_rag", lambda query, **kw: "answer")

        try:
            resp = routes_query.ask(
                payload=routes_query.QueryRequest(
                    query="test",
                    mode="no-rag",
                    compliance_confirmed=True,
                    compliance_reason="unit test",
                    operation_id="op-guard-1",
                ),
                user=user,
                db=db_session,
            )
            assert resp["compliance_confirmed"] is True
            assert resp["compliance_bypassed"] is False
        finally:
            compliance.set_compliance_enforcement_override(None)


# ---------------------------------------------------------------------------
# 2. Operator confirmation – audit log records who, when, action, request_id
# ---------------------------------------------------------------------------

class TestOperatorConfirmationAuditLog:
    """Each compliance decision must be persisted in the audit_logs table."""

    def test_confirmed_action_creates_audit_entry(self, db_session, user_factory):
        compliance.set_compliance_enforcement_override(True)
        user = user_factory("operator1", "pass", role="Curator")
        token = set_request_id("req-audit-1")

        try:
            decision = compliance.resolve_sensitive_action_compliance(
                db=db_session,
                user=user,
                action_type="ingest.run",
                operation_id="op-audit-1",
                compliance_confirmed=True,
                compliance_reason="scheduled crawl",
                compliance_bypassed=False,
            )
            db_session.commit()
        finally:
            compliance.set_compliance_enforcement_override(None)
            reset_request_id(token)

        entry = db_session.query(AuditLog).filter(AuditLog.action == "compliance.confirmed").first()
        assert entry is not None
        assert entry.user_id == user.id
        meta = json.loads(entry.metadata_json)
        assert meta["operation_id"] == "op-audit-1"
        assert meta["action_type"] == "ingest.run"
        assert meta["reason"] == "scheduled crawl"
        assert meta["request_id"] == "req-audit-1"

    def test_bypassed_action_creates_audit_entry(self, db_session, user_factory):
        compliance.set_compliance_enforcement_override(False)
        user = user_factory("operator2", "pass", role="User")

        try:
            decision = compliance.resolve_sensitive_action_compliance(
                db=db_session,
                user=user,
                action_type="query.execute",
                operation_id="op-audit-2",
                compliance_confirmed=False,
                compliance_reason="",
                compliance_bypassed=True,
            )
            db_session.commit()
        finally:
            compliance.set_compliance_enforcement_override(None)

        entry = db_session.query(AuditLog).filter(AuditLog.action == "compliance.bypassed").first()
        assert entry is not None
        assert entry.user_id == user.id
        meta = json.loads(entry.metadata_json)
        assert meta["compliance_bypassed"] is True

    def test_audit_entry_includes_timestamp(self, db_session, user_factory):
        compliance.set_compliance_enforcement_override(False)
        user = user_factory("operator3", "pass", role="User")

        try:
            compliance.resolve_sensitive_action_compliance(
                db=db_session,
                user=user,
                action_type="query.execute",
                operation_id="op-ts-check",
                compliance_confirmed=False,
                compliance_bypassed=True,
            )
            db_session.commit()
        finally:
            compliance.set_compliance_enforcement_override(None)

        entry = db_session.query(AuditLog).order_by(AuditLog.id.desc()).first()
        assert entry is not None
        assert entry.ts is not None


# ---------------------------------------------------------------------------
# 3. API blocks without confirmation (server-side enforcement, not just FE)
# ---------------------------------------------------------------------------

class TestAPIEnforcementServerSide:
    """The API must reject requests independently of the frontend guard."""

    def test_ingest_api_rejects_missing_confirmation_field(self, monkeypatch, db_session, source):
        compliance.set_compliance_enforcement_override(True)
        user = SimpleNamespace(id=1, role="Curator")
        monkeypatch.setattr(routes_ingest, "run_ingest", lambda **kw: {"status": "completed", "document_id": 1})

        try:
            with pytest.raises(HTTPException) as exc:
                routes_ingest.ingest_url(
                    payload=routes_ingest.IngestRequest(
                        source_id=source.id,
                        url=f"{source.base_url}/page",
                        compliance_confirmed=False,
                    ),
                    user=user,
                    db=db_session,
                )
            assert exc.value.status_code == 422
        finally:
            compliance.set_compliance_enforcement_override(None)

    def test_query_api_rejects_missing_confirmation_field(self, monkeypatch, db_session):
        compliance.set_compliance_enforcement_override(True)
        user = SimpleNamespace(id=1, role="User")
        monkeypatch.setattr(routes_query, "answer_no_rag", lambda query, **kw: "x")

        try:
            with pytest.raises(HTTPException) as exc:
                routes_query.ask(
                    payload=routes_query.QueryRequest(
                        query="test",
                        mode="no-rag",
                        compliance_confirmed=False,
                    ),
                    user=user,
                    db=db_session,
                )
            assert exc.value.status_code == 422
        finally:
            compliance.set_compliance_enforcement_override(None)

    def test_ingest_api_accepts_with_confirmation(self, monkeypatch, db_session, source):
        compliance.set_compliance_enforcement_override(True)
        user = SimpleNamespace(id=1, role="Curator")
        monkeypatch.setattr(routes_ingest, "run_ingest", lambda **kw: {"status": "completed", "document_id": 1})

        try:
            resp = routes_ingest.ingest_url(
                payload=routes_ingest.IngestRequest(
                    source_id=source.id,
                    url=f"{source.base_url}/page",
                    compliance_confirmed=True,
                    compliance_reason="API test",
                    operation_id="op-api-ok",
                ),
                user=user,
                db=db_session,
            )
            assert resp["compliance_confirmed"] is True
            assert resp["operation_id"] == "op-api-ok"
        finally:
            compliance.set_compliance_enforcement_override(None)


# ---------------------------------------------------------------------------
# 4. COMPLIANCE_ENFORCEMENT toggle – dev mode vs prod
# ---------------------------------------------------------------------------

class TestComplianceEnforcementToggle:
    """The enforcement toggle must switch behavior in both API and decision logic."""

    def test_dev_mode_allows_without_confirmation(self, monkeypatch, db_session):
        compliance.set_compliance_enforcement_override(False)
        user = SimpleNamespace(id=1, role="User")
        monkeypatch.setattr(routes_query, "answer_no_rag", lambda query, **kw: "answer")

        try:
            resp = routes_query.ask(
                payload=routes_query.QueryRequest(query="test", mode="no-rag"),
                user=user,
                db=db_session,
            )
            assert resp["compliance_bypassed"] is True
            assert resp["compliance_confirmed"] is False
        finally:
            compliance.set_compliance_enforcement_override(None)

    def test_prod_mode_rejects_without_confirmation(self, monkeypatch, db_session):
        compliance.set_compliance_enforcement_override(True)
        user = SimpleNamespace(id=1, role="User")
        monkeypatch.setattr(routes_query, "answer_no_rag", lambda query, **kw: "answer")

        try:
            with pytest.raises(HTTPException) as exc:
                routes_query.ask(
                    payload=routes_query.QueryRequest(query="test", mode="no-rag"),
                    user=user,
                    db=db_session,
                )
            assert exc.value.status_code == 422
        finally:
            compliance.set_compliance_enforcement_override(None)

    def test_runtime_override_toggles_mode(self):
        compliance.set_compliance_enforcement_override(None)
        admin = SimpleNamespace(id=1, role="Admin")
        viewer = SimpleNamespace(id=2, role="User")

        before = routes_compliance.get_mode(user=viewer)

        routes_compliance.set_mode(
            payload=routes_compliance.ComplianceModeUpdateRequest(enforcement=not before["enforcement"]),
            user=admin,
        )
        after = routes_compliance.get_mode(user=viewer)

        compliance.set_compliance_enforcement_override(None)

        assert after["enforcement"] != before["enforcement"]
        assert after["source"] == "runtime_override"

    def test_compliance_history_endpoint_returns_entries(self, db_session, user_factory):
        compliance.set_compliance_enforcement_override(False)
        user = user_factory("hist_user", "pass", role="User")

        try:
            compliance.resolve_sensitive_action_compliance(
                db=db_session,
                user=user,
                action_type="ingest.run",
                operation_id="op-hist-1",
                compliance_confirmed=False,
                compliance_bypassed=True,
            )
            db_session.commit()
        finally:
            compliance.set_compliance_enforcement_override(None)

        history = routes_compliance.history(limit=10, user=user, db=db_session)
        assert len(history) >= 1
        assert history[0]["action"] == "ingest.run"
        assert history[0]["compliance_bypassed"] is True

    def test_decision_returns_operation_id(self, db_session, user_factory):
        compliance.set_compliance_enforcement_override(False)
        user = user_factory("op_id_user", "pass", role="User")

        try:
            decision = compliance.resolve_sensitive_action_compliance(
                db=db_session,
                user=user,
                action_type="query.execute",
                operation_id="op-custom-123",
                compliance_confirmed=False,
                compliance_bypassed=True,
            )
            db_session.commit()
        finally:
            compliance.set_compliance_enforcement_override(None)

        assert decision.operation_id == "op-custom-123"

    def test_decision_generates_operation_id_when_not_provided(self, db_session, user_factory):
        compliance.set_compliance_enforcement_override(False)
        user = user_factory("auto_id_user", "pass", role="User")

        try:
            decision = compliance.resolve_sensitive_action_compliance(
                db=db_session,
                user=user,
                action_type="query.execute",
                compliance_confirmed=False,
                compliance_bypassed=True,
            )
            db_session.commit()
        finally:
            compliance.set_compliance_enforcement_override(None)

        assert decision.operation_id is not None
        assert decision.operation_id.startswith("op-")
