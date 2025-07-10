from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# App-level OpenAPI tags metadata
openapi_tags = [
    {
        "name": "Health",
        "description": "Health check endpoints"
    },
    {
        "name": "Metrics",
        "description": "Endpoints to retrieve app metrics and summary statistics"
    }
]

app = FastAPI(
    title="App Metrics Dashboard Backend",
    description="API for serving application generation metrics, with endpoints for health check and metrics retrieval, using mock data.",
    version="1.0.0",
    openapi_tags=openapi_tags
)

# Enable CORS for all origins for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check", response_description="Healthy status response")
def health_check():
    """Health check endpoint to confirm that the backend is running.
    Returns a 200 response with a health message.

    Returns:
        JSON with message "Healthy"
    """
    return {"message": "Healthy"}

# --- DATA MODELS ---

# PUBLIC_INTERFACE
class MetricEntry(BaseModel):
    """Represents a single application generation metric entry."""
    id: int = Field(..., description="Unique identifier of the metric entry")
    project_name: str = Field(..., description="Name of the generated project")
    status: Literal["SUCCESS", "FAILED", "RUNNING"] = Field(..., description="Status of the generation instance")
    duration_seconds: float = Field(..., description="Time taken (seconds)")
    created_at: datetime = Field(..., description="Timestamp when generation started")
    completed_at: Optional[datetime] = Field(None, description="Timestamp when generation completed")
    user_email: str = Field(..., description="_email of the user who initiated the generation")
    cost_usd: float = Field(..., description="Cost (in USD) for the generation")
    details_url: str = Field(..., description="URL to project details")
    project_type: str = Field(..., description="Type/category of the generated project")

# PUBLIC_INTERFACE
class MetricsSummary(BaseModel):
    total_count: int = Field(..., description="Total number of metric entries in the query result")
    average_duration: float = Field(..., description="Average duration (in seconds) across matched entries")
    total_cost: float = Field(..., description="Sum of 'cost_usd' for all matched entries")
    success_count: int = Field(..., description="Number of successful generations")
    failed_count: int = Field(..., description="Number of failed generations")

# PUBLIC_INTERFACE
class MetricsResponse(BaseModel):
    data: List[MetricEntry] = Field(..., description="List of metrics on this page")
    summary: MetricsSummary = Field(..., description="Summary statistics for the query")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

# --- MOCK DATA GENERATOR ---

import random
from datetime import timedelta

def _generate_mock_metrics(n=60):
    projects = ["ImageGen", "SalesCRM", "AI Chatbot", "DashboardPro", "VideoMaker", "SiteBuilder"]
    project_types = ["Web App", "AI", "CRM", "Dashboard", "Media", "Builder"]
    users = ["alice@example.com", "bob@example.com", "carol@example.com", "dan@example.com"]
    base_url = "https://app.example.com/projects/"
    mock_metrics = []
    now = datetime.utcnow()
    for i in range(n):
        duration = round(random.uniform(8, 180), 2)
        # Correctly use datetime.timedelta for offset, not random.timedelta
        created = now.replace(microsecond=0) - timedelta(days=random.randint(0, 30), hours=random.randint(0,23), minutes=random.randint(0,59))
        status = random.choices(["SUCCESS", "FAILED", "RUNNING"], [0.7, 0.2, 0.1])[0]
        completed = None
        if status != "RUNNING":
            completed = created
        entry = {
            "id": i+1,
            "project_name": random.choice(projects) + f"-{i+1:04d}",
            "status": status,
            "duration_seconds": duration,
            "created_at": created,
            "completed_at": completed,
            "user_email": random.choice(users),
            "cost_usd": round(duration * 0.08 + random.uniform(0.10, 5.0), 2),
            "details_url": base_url + str(i+1),
            "project_type": random.choice(project_types),
        }
        mock_metrics.append(entry)
    return mock_metrics

# Use a fixed seed so mock data is deterministic per run
random.seed(42)

# Generate global mock data
MOCK_METRICS = [MetricEntry(**m) for m in _generate_mock_metrics()]

# --- METRICS ENDPOINT ---

# PUBLIC_INTERFACE
@app.get(
    "/metrics",
    response_model=MetricsResponse,
    tags=["Metrics"],
    summary="Get metrics data",
    description="""
Get a paginated, filterable, and sortable list of app generation metrics for dashboard display.

Supports search, date range filtering, project type filter, status filter, sorting, and pagination.

**Query Parameters:**
- `page` (int, default 1): Page number (starts at 1)
- `page_size` (int, default 15): Page size for pagination (max 100)
- `search` (str, optional): Search term for project name or user email
- `date_from` (str, optional): ISO date string filter (created_at >= date_from)
- `date_to` (str, optional): ISO date string filter (created_at <= date_to)
- `status` (str, optional): Filter by status ("SUCCESS", "FAILED", "RUNNING")
- `project_type` (str, optional): Filter by project type
- `sort_by` (str, optional): Sort field (id, created_at, duration_seconds, cost_usd, status, project_name)
- `sort_order` (str, optional): "asc" or "desc"

Returns paged data for dashboard and summary statistics.
"""
)
def get_metrics(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(15, ge=1, le=100, description="Number of items per page"),
    search: Optional[str] = Query(None, description="Search by project name or user email"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: Optional[Literal["SUCCESS", "FAILED", "RUNNING"]] = Query(None, description="Status filter"),
    project_type: Optional[str] = Query(None, description="Project type filter"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[Literal["asc", "desc"]] = Query("desc", description="Sort order (asc/desc)")
):
    """
    Retrieve metrics entries filtered and paginated.
    - Filtering, searching, sorting, and pagination are done in-memory for mock data.
    - This route is ready for real DB or S3 integration in the future.
    Returns:
        MetricsResponse: Paged metric data and summary.
    """

    # Filtering, searching
    data = MOCK_METRICS.copy()
    if search:
        s = search.lower()
        data = [d for d in data if s in d.project_name.lower() or s in d.user_email.lower()]
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            data = [d for d in data if d.created_at >= from_date]
        except Exception:
            pass
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            data = [d for d in data if d.created_at <= to_date]
        except Exception:
            pass
    if status:
        data = [d for d in data if d.status == status]
    if project_type:
        data = [d for d in data if d.project_type.lower() == project_type.lower()]

    # Sorting
    sort_field = sort_by if sort_by in MetricEntry.model_fields else "created_at"
    reverse = (sort_order == "desc")
    try:
        data = sorted(data, key=lambda x: getattr(x, sort_field), reverse=reverse)
    except Exception:
        pass

    # Pagination
    total_count = len(data)
    total_pages = max(1, ((total_count - 1) // page_size) + 1)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    page_data = data[start:end]

    # Summary stats
    avg_duration = round(sum([d.duration_seconds for d in data]) / total_count, 2) if total_count > 0 else 0.0
    total_cost = round(sum([d.cost_usd for d in data]), 2)
    success_count = sum([d.status == "SUCCESS" for d in data])
    failed_count = sum([d.status == "FAILED" for d in data])

    summary = MetricsSummary(
        total_count=total_count,
        average_duration=avg_duration,
        total_cost=total_cost,
        success_count=success_count,
        failed_count=failed_count
    )
    resp = MetricsResponse(
        data=page_data,
        summary=summary,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
    # Return as a Pydantic model so FastAPI handles JSON serialization (including datetime)
    return resp
