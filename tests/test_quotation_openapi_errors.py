from app.main import _admin_openapi, fastapi_app


def test_admin_quotation_error_examples_match_http_statuses():
    schema = fastapi_app.openapi()
    operations = schema["paths"]

    cases = [
        ("/api/v1/admin/quotations", "post", "401", "UNAUTHORIZED"),
        ("/api/v1/admin/quotations", "post", "404", "NOT_FOUND"),
        ("/api/v1/admin/quotations", "post", "409", "CONFLICT"),
        ("/api/v1/admin/quotations", "post", "422", "VALIDATION_ERROR"),
        ("/api/v1/admin/quotations/{quotation_id}/convert", "post", "400", "BAD_REQUEST"),
        ("/api/v1/admin/quotations/{quotation_id}/convert", "post", "422", "VALIDATION_ERROR"),
    ]

    for path, method, status_code, expected_code in cases:
        response = operations[path][method]["responses"][status_code]
        example = response["content"]["application/json"]["example"]

        assert example["success"] is False
        assert example["error"]["code"] == expected_code
        assert response["description"]


def test_error_payload_documents_required_nullable_details():
    schema = fastapi_app.openapi()
    error_payload = schema["components"]["schemas"]["ErrorPayload"]

    assert "details" in error_payload["required"]
    assert {"type": "null"} in error_payload["properties"]["details"]["anyOf"]


def test_admin_docs_examples_show_null_details_for_errors_without_details():
    schema = _admin_openapi()
    example = schema["paths"]["/api/v1/admin/quotations"]["post"]["responses"]["401"][
        "content"
    ]["application/json"]["example"]

    assert example["error"]["details"] is None
