from datetime import datetime, timezone
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import ForecastHistory
from ..services.forecasting import ForecastingError, ForecastingService

forecasting_blueprint = Blueprint("forecasting", __name__)


def _service():
    service = current_app.extensions.get("forecasting_service")
    if service is None:
        service = ForecastingService()
        current_app.extensions["forecasting_service"] = service
    return service


def _user_id():
    try:
        return int(get_jwt_identity())
    except (TypeError, ValueError):
        return None


def _serialize(record):
    return {
        "id": record.id,
        "forecast_year": record.forecast_year,
        "state": record.state,
        "district": record.district,
        "risk": record.risk,
        "confidence": record.confidence,
        "expected_trend": record.expected_trend,
        "projected_cases": record.projected_cases,
        "climate_summary": record.climate_summary,
        "timeline": record.timeline,
        "recommendations": record.recommendations,
        "generated_at": record.generated_at.isoformat(),
    }


@forecasting_blueprint.get("/forecast/options")
@jwt_required()
def forecast_options():
    try:
        return jsonify(_service().options()), 200
    except ForecastingError as error:
        current_app.logger.exception("Forecast source data is unavailable")
        return jsonify({"message": str(error), "error": "forecast_data_unavailable"}), 503


@forecasting_blueprint.get("/forecast/trends")
@jwt_required()
def forecast_trends():
    state = request.args.get("state", "")
    try:
        years = int(request.args.get("years", "5"))
        return jsonify(_service().trends(state, years)), 200
    except ValueError as error:
        return jsonify({"message": str(error), "error": "invalid_forecast_request"}), 400
    except ForecastingError as error:
        current_app.logger.exception("Forecast climate trends are unavailable")
        return jsonify({"message": str(error), "error": "forecast_data_unavailable"}), 503


@forecasting_blueprint.post("/forecast")
@jwt_required()
def create_forecast():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"message": "A JSON object is required."}), 400
    allowed_fields = {"forecast_year", "state", "district"}
    if payload.keys() - allowed_fields:
        return jsonify({"message": "Unsupported forecast request fields were provided."}), 400
    try:
        result = _service().forecast(
            payload.get("state"),
            payload.get("forecast_year"),
            payload.get("district"),
        )
    except ValueError as error:
        return jsonify({"message": str(error), "error": "invalid_forecast_request"}), 400
    except ForecastingError as error:
        current_app.logger.exception("Forecast could not be generated")
        return jsonify({"message": str(error), "error": "forecast_data_unavailable"}), 503

    record = ForecastHistory(
        user_id=_user_id(),
        forecast_year=result["forecast_year"],
        state=result["state"],
        district=result["district"],
        risk=result["risk"],
        confidence=result["confidence"],
        expected_trend=result["expected_trend"],
        projected_cases=result["projected_cases"],
        climate_summary=result["climate_summary"],
        timeline=result["timeline"],
        recommendations=result["recommendations"],
        generated_at=datetime.now(timezone.utc),
    )
    try:
        db.session.add(record)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not save generated forecast")
        return jsonify({"message": "Forecast generated but could not be saved.", "error": "database_error"}), 500
    return jsonify({**result, "id": record.id, "generated_at": record.generated_at.isoformat()}), 201


@forecasting_blueprint.get("/forecast/history")
@jwt_required()
def forecast_history():
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", request.args.get("limit", "20")))
    except ValueError:
        return jsonify({"message": "page and per_page must be integers."}), 400
    if page < 1 or not 1 <= per_page <= 100:
        return jsonify({"message": "page must be >= 1 and per_page must be between 1 and 100."}), 400
    try:
        pagination = (
            ForecastHistory.query.filter_by(user_id=_user_id())
            .order_by(ForecastHistory.generated_at.desc(), ForecastHistory.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )
    except SQLAlchemyError:
        current_app.logger.exception("Could not retrieve forecast history")
        return jsonify({"message": "Forecast history could not be retrieved."}), 500
    return jsonify({
        "items": [_serialize(record) for record in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_previous": pagination.has_prev,
        },
    }), 200


@forecasting_blueprint.get("/forecast/map")
@jwt_required()
def forecast_map():
    try:
        forecast_year = int(request.args.get("year", ""))
        items = _service().map_forecasts(forecast_year)
    except ValueError as error:
        return jsonify({"message": str(error), "error": "invalid_forecast_request"}), 400
    except ForecastingError as error:
        current_app.logger.exception("Forecast map data is unavailable")
        return jsonify({"message": str(error), "error": "forecast_data_unavailable"}), 503
    return jsonify({"items": items, "count": len(items), "forecast_year": forecast_year}), 200


@forecasting_blueprint.get("/forecast/history/<int:forecast_id>/report.pdf")
@jwt_required()
def forecast_report(forecast_id):
    record = ForecastHistory.query.filter_by(
        id=forecast_id, user_id=_user_id()
    ).first()
    if record is None:
        return jsonify({"message": "Forecast report was not found."}), 404

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ForecastTitle", parent=styles["Title"], textColor=colors.HexColor("#155e63"),
        alignment=TA_CENTER, spaceAfter=10,
    )
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )
    story = [
        Paragraph("Dengue Forecast Report", title_style),
        Paragraph(
            f"<b>Forecast year:</b> {record.forecast_year} &nbsp;&nbsp; "
            f"<b>State:</b> {record.state} &nbsp;&nbsp; "
            f"<b>District:</b> {record.district or 'State-level'}",
            styles["BodyText"],
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            f"<b>Projected risk:</b> {record.risk}<br/>"
            f"<b>Trend:</b> {record.expected_trend}<br/>"
            f"<b>Heuristic confidence:</b> {record.confidence:.1f}%<br/>"
            f"<b>Estimated reported cases:</b> {record.projected_cases:,.0f}<br/>"
            f"<b>Generated:</b> {record.generated_at.isoformat()}",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("Historical and forecast risk timeline", styles["Heading2"]),
        _timeline_chart(record.timeline),
        Spacer(1, 3 * mm),
        Paragraph("Historical climate trend summary", styles["Heading2"]),
        _climate_table(record.climate_summary),
        Spacer(1, 3 * mm),
        Paragraph("Suggested public health actions", styles["Heading2"]),
    ]
    story.extend(Paragraph(f"• {item}", styles["BodyText"]) for item in record.recommendations)
    story.extend(
        [
            Spacer(1, 4 * mm),
            Paragraph(
                "Exploratory linear trend projection from complete historical state-level data. "
                "Confidence is a heuristic fit indicator, not a calibrated probability. "
                "This report is not medical advice.",
                styles["Italic"],
            ),
        ]
    )
    document.build(story)
    buffer.seek(0)
    return send_file(
        buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"dengue-forecast-{record.id}.pdf",
    )


def _timeline_chart(timeline):
    drawing = Drawing(470, 150)
    if not timeline:
        drawing.add(String(10, 70, "No historical data available.", fontSize=9))
        return drawing
    values = [float(item["confirmed_cases"]) for item in timeline]
    max_value = max(max(values), 1)
    left, bottom, width, height = 42, 30, 400, 95
    drawing.add(Line(left, bottom, left + width, bottom, strokeColor=colors.grey))
    drawing.add(Line(left, bottom, left, bottom + height, strokeColor=colors.grey))
    points = []
    for index, item in enumerate(timeline):
        x = left + (width * index / max(1, len(timeline) - 1))
        y = bottom + height * float(item["confirmed_cases"]) / max_value
        points.append((x, y))
        drawing.add(String(x - 12, bottom - 15, str(item["year"]), fontSize=7))
        drawing.add(Circle(
            x, y, 4,
            fillColor=colors.HexColor("#d97706") if item["kind"] == "forecast" else colors.HexColor("#0f766e"),
            strokeColor=colors.white,
        ))
    for first, second in zip(points, points[1:]):
        drawing.add(Line(*first, *second, strokeColor=colors.HexColor("#0f766e"), strokeWidth=1.8))
    drawing.add(String(left, bottom + height + 8, "Estimated dengue cases", fontSize=8))
    return drawing


def _climate_table(history):
    rows = [["Year", "Temp °C", "Humidity %", "Rain mm", "Wind m/s", "Solar MJ/m²"]]
    rows.extend(
        [
            str(item["year"]),
            f'{item["temperature"]:.1f}',
            f'{item["humidity"]:.1f}',
            f'{item["rainfall"]:.0f}',
            f'{item["wind_speed"]:.1f}',
            f'{item["solar_radiation"]:.1f}',
        ]
        for item in history[-5:]
    )
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f3f2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#155e63")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d4e1e0")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table
