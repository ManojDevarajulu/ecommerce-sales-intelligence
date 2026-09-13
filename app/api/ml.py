"""
app/api/ml.py — T113: `POST /ml/predict`, wiring `ml/predict.py` (T110/T111)
into the FastAPI app the same way `app/api/analytics.py` wires up
`app/services/analytics.py` - the ML logic itself stays in `ml/`, this
module is just the HTTP layer + `get_db` plumbing on top of it.
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
        # An unrecognized categorical value (build_feature_row's guard) or a
        # non-positive gross_sales - a client input problem (422-ish), not a
        # server error, even though it's only caught this deep in the stack.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PredictResponse(
        return_probability=probability,
        predicted_label="Returned" if probability >= 0.5 else "Not Returned",
        contributing_factors=explain_contributing_factors(X),
    )
