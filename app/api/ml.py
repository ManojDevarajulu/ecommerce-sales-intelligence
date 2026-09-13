"""
app/api/ml.py — `POST /ml/predict`.

Thin HTTP layer over `ml/predict.py`, the same way `app/api/analytics.py`
sits over `app/services/analytics.py`: the model loading, feature building
and scoring all stay in `ml/`, and this module only unpacks the request,
supplies the database session, and maps errors to status codes. Keeping
the split means the model can be retrained or swapped without touching
any API code.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ml import PredictRequest, PredictResponse
from ml.predict import explain_contributing_factors, predict_return_probability

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest, db: Session = Depends(get_db)) -> PredictResponse:
    order = {
        "customer_id": request.customer_id,
        "gross_sales": float(request.gross_sales),
        "shipping_cost": float(request.shipping_cost),
        "sales_channel": request.sales_channel.value,
        "payment_method": request.payment_method.value,
        "shipping_method": request.shipping_method.value,
        "region": request.region.value,
        "primary_category": request.primary_category.value,
    }
    try:
        probability, X = predict_return_probability(order, db)
    except ValueError as exc:
        # Raised by build_feature_row for an unrecognized categorical value
        # or a non-positive gross_sales. That is a problem with the client's
        # input, not a server fault - it just happens to be detected deep in
        # the feature-building code rather than at the schema boundary.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PredictResponse(
        return_probability=probability,
        predicted_label="Returned" if probability >= 0.5 else "Not Returned",
        contributing_factors=explain_contributing_factors(X),
    )
