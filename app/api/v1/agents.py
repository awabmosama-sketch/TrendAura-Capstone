from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.fraud import run_fraud_pipeline
from app.agents.onboarding import generate_product_content
from app.agents.recommendations import discover_products
from app.core.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.agent_log import AgentAuditLog, FraudFlag
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/recommendations")
async def recommendations(
    q: str,
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    results = await discover_products(q, db, user.id if user else None)
    return {
        "query": q,
        "parsed": {"max_price": next((item for item in q.split() if item.isdigit()), None)},
        "recommendations": [
            {"score": item["score"], "matched_terms": item["matched_terms"], "product": ProductResponse.model_validate(item["product"]).model_dump(mode="json")}
            for item in results
        ],
    }


@router.post("/onboarding", status_code=201)
async def onboard_product(
    name: str = Form(...),
    category_id: int = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(0),
    sku: str = Form(...),
    image_url: str = Form("https://images.unsplash.com/photo-1525507119028-ed4c629a60a3"),
    image: UploadFile | None = File(None),
    _: User = Depends(require_roles("admin", "vendor")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    content = generate_product_content(name, category.name)
    product = Product(name=name, slug=content["slug"], sku=sku, description=content["description"], price=price, stock_quantity=stock_quantity, category_id=category_id, image_url=image_url, images=[])
    db.add(product)
    db.add(AgentAuditLog(agent_name="product_onboarding", status="success", input_state={"name": name, "category": category.name, "image_filename": image.filename if image else None}, output_state=content))
    await db.commit()
    await db.refresh(product)
    return {"product": ProductResponse.model_validate(product).model_dump(mode="json"), "seo_tags": content["seo_tags"]}


async def create_fraud_flag(order: Order, db: AsyncSession) -> dict:
    state = run_fraud_pipeline(order)
    order.fraud_score = state["fraud_score"]
    order.fraud_flags = state["flags"]
    if state["verdict"] == "Flagged":
        db.add(FraudFlag(order_id=order.id, fraud_score=state["fraud_score"], verdict=state["verdict"], flags=state["flags"]))
    return state
