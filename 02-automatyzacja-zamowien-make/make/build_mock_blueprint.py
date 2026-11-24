"""Generuje make/blueprints/02-mock-api.blueprint.json – scenariusz udający API Fakturowni i InPost ShipX.
Tylko moduły wbudowane (Webhook, Tools, Router, Webhook response), więc import nie wymaga żadnych połączeń."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "blueprints" / "02-mock-api.blueprint.json"
JSON_HEADERS = [{"key": "Content-Type", "value": "application/json"}]


def respond(mid, x, status, body, filter_name, conditions):
    m = {"id": mid, "module": "gateway:WebhookRespond", "version": 1, "parameters": {},
         "mapper": {"status": str(status), "body": body, "headers": JSON_HEADERS},
         "metadata": {"designer": {"x": x, "y": 0}}}
    if conditions:
        m["filter"] = {"name": filter_name, "conditions": conditions}
    return m


invoice_body = """{
  "id": {{2.doc_id}},
  "number": "FV/{{formatDate(now; "YYYY/MM")}}/{{2.doc_id}}",
  "kind": "vat",
  "status": "issued",
  "buyer_name": "{{1.invoice.buyer_name}}",
  "oid": "{{1.invoice.oid}}",
  "view_url": "https://vitaforge-demo.fakturownia.pl/invoice/{{2.doc_id}}"
}"""

shipment_body = """{
  "id": {{2.doc_id}},
  "status": "created",
  "service": "{{1.service}}",
  "tracking_number": "{{2.tracking}}",
  "reference": "{{1.reference}}"
}"""

blueprint = {
    "name": "VitaForge · 02 Mock API (Fakturownia + InPost)",
    "flow": [
        {"id": 1, "module": "gateway:CustomWebHook", "version": 1,
         "parameters": {"hook": None, "maxResults": 1},
         "mapper": {}, "metadata": {"designer": {"x": 0, "y": 0}}},
        {"id": 2, "module": "util:SetVariables", "version": 1, "parameters": {},
         "mapper": {"scope": "roundtrip", "variables": [
             {"name": "doc_id", "value": "{{floor(random * 900000) + 100000}}"},
             {"name": "tracking", "value": "65{{formatDate(now; \"YYMMDDHHmmssSSS\")}}{{floor(random * 9000000) + 1000000}}"},
         ]},
         "metadata": {"designer": {"x": 300, "y": 0}}},
        {"id": 3, "module": "builtin:BasicRouter", "version": 1, "mapper": None,
         "metadata": {"designer": {"x": 600, "y": 0}},
         "routes": [
             {"flow": [respond(4, 900, 201, invoice_body, "Faktura (Fakturownia)",
                               [[{"a": "{{1.mock}}", "o": "text:equal", "b": "invoice"}]])]},
             {"flow": [respond(5, 900, 201, shipment_body, "Przesyłka (InPost ShipX)",
                               [[{"a": "{{1.mock}}", "o": "text:equal", "b": "shipment"}]])]},
             {"flow": [respond(6, 900, 400, '{"error": "unknown mock service: {{1.mock}}"}', "Nieznana usługa",
                               [[{"a": "{{1.mock}}", "o": "text:notequal", "b": "invoice"},
                                 {"a": "{{1.mock}}", "o": "text:notequal", "b": "shipment"}]])]},
         ]},
    ],
    "metadata": {
        "instant": True, "version": 1,
        "scenario": {"roundtrips": 1, "maxErrors": 3, "autoCommit": True, "autoCommitTriggerLast": True,
                     "sequential": False, "confidential": False, "dataloss": False, "dlq": False,
                     "freshVariables": False},
        "designer": {"orphans": []},
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Zapisano {OUT.name}")
