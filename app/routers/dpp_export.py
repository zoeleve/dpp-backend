import json
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from app.db.database_postgre import get_db
from app.models.dpp import DPP

router = APIRouter(prefix="/dpp/export", tags=["DPP Export"])

@router.get("/{dpp_id}")
async def export_dpp(dpp_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Search for the DPP in the database
    dpp_record = await db.get(DPP, dpp_id)
    
    # 2. Check if it exists
    if not dpp_record:
        raise HTTPException(status_code=404, detail="DPP not found")
    
    # 3. Return the data (Here you can convert it to PDF/JSON)
    return {
        "message": "Export successful",
        "data": dpp_record
    }

@router.get("/{dpp_id}/pdf")
async def export_dpp_pdf(dpp_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Search for the DPP in the database
    dpp_record = await db.get(DPP, dpp_id)

    # 2. Check if it exists
    if not dpp_record:
        raise HTTPException(status_code=404, detail="DPP not found")

    # 3. Generate PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"DPP Export: {dpp_record.title}")

    # Metadata
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"ID: {dpp_record.id}")
    c.drawString(50, height - 100, f"UUID: {dpp_record.dpp_uuid}")
    
    # Removed Owner ID for privacy
    # c.drawString(50, height - 120, f"Owner ID: {dpp_record.owner_id}")
    
    c.drawString(50, height - 120, f"Status: {'Published' if dpp_record.is_published else 'Draft'}")
    
    # Try to get Manufacturer from dpp_data
    manufacturer = dpp_record.dpp_data.get("manufacturer", "N/A") if dpp_record.dpp_data else "N/A"
    c.drawString(50, height - 140, f"Manufacturer: {manufacturer}")

    # Content (JSON Data)
    c.drawString(50, height - 170, "DPP Data:")
    c.setFont("Courier", 10)

    y_position = height - 190
    if dpp_record.dpp_data:
        # Pretty print JSON
        json_str = json.dumps(dpp_record.dpp_data, indent=2)
        for line in json_str.split('\n'):
            # Simple pagination check
            if y_position < 50:
                c.showPage()
                c.setFont("Courier", 10)
                y_position = height - 50
            c.drawString(50, y_position, line)
            y_position -= 12
    else:
        c.drawString(50, y_position, "No data available.")

    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=dpp_{dpp_record.dpp_uuid}.pdf"}
    )