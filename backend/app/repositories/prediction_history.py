from sqlalchemy import func

from ..extensions import db
from ..models import PredictionHistory


def save_prediction(user_id: int, payload: dict) -> PredictionHistory:
    record = PredictionHistory(
        user_id=user_id, state=payload["state"], temperature=payload["temperature"],
        humidity=payload["humidity"], rainfall=payload["rainfall"],
        wind_speed=payload["wind_speed"], pressure=payload["pressure"],
        solar_radiation=payload["solar_radiation"], year=payload["year"],
        prediction=payload["risk_level"], confidence=payload["confidence"],
        class_probabilities=payload["class_probabilities"],
        recommendations=payload["recommendations"],
        prediction_time=payload["prediction_time"],
    )
    db.session.add(record)
    db.session.commit()
    return record


def prediction_query(user_id: int | None, search: str | None = None, risk: str | None = None):
    query = PredictionHistory.query
    if user_id is not None:
        query = query.filter(PredictionHistory.user_id == user_id)
    if search:
        query = query.filter(PredictionHistory.state.ilike(f"%{search}%"))
    if risk:
        query = query.filter(PredictionHistory.prediction == risk)
    return query


def list_predictions(user_id: int | None, page: int, per_page: int, search: str | None = None, risk: str | None = None):
    return prediction_query(user_id, search, risk).order_by(
        PredictionHistory.prediction_time.desc(), PredictionHistory.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)


def delete_prediction(prediction_id: int, user_id: int | None) -> bool:
    query = PredictionHistory.query.filter_by(id=prediction_id)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    record = query.first()
    if record is None:
        return False
    db.session.delete(record)
    db.session.commit()
    return True


def latest_prediction(user_id: int | None):
    query = PredictionHistory.query
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    return query.order_by(PredictionHistory.prediction_time.desc(), PredictionHistory.id.desc()).first()


def prediction_count(user_id: int | None) -> int:
    query = PredictionHistory.query
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    return query.count()


def risk_distribution(user_id: int | None) -> dict[str, int]:
    query = db.session.query(PredictionHistory.prediction, func.count(PredictionHistory.id))
    if user_id is not None:
        query = query.filter(PredictionHistory.user_id == user_id)
    return {risk: int(count) for risk, count in query.group_by(PredictionHistory.prediction).all()}
