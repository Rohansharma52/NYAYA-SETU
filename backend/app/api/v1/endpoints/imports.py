"""CSV import endpoints for institutions and cases."""
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.import_job import ImportJob, ImportRow, ImportStatus
from app.models.institution import Institution
from app.models.case import Case, CaseStatus, CasePriority
from app.models.user import User, UserRole
from app.services.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/imports", tags=["imports"])

INSTITUTION_REQUIRED_COLS = {"canonical_name"}
CASE_REQUIRED_COLS = {"title", "category", "institution_id"}


class ImportJobOut(BaseModel):
    id: int
    filename: str
    import_type: str
    status: str
    total_rows: int
    valid_rows: int
    error_rows: int
    imported_rows: int
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    class Config: from_attributes = True


def _validate_institution_row(row: dict, row_num: int) -> tuple:
    errors, warnings = [], []
    if not row.get("canonical_name", "").strip():
        errors.append("canonical_name is required")
    return errors, warnings


def _resolve_row_institution(row: dict, db: Session, profiles_cache: dict):
    """Use the Identity Resolution Engine when a CSV row has no institution_id
    (e.g. CPGRAMS exports carry only the institution name as typed by the citizen)."""
    from app.services.identity import resolve
    from app.services.intelligence import institution_profiles
    if "profiles" not in profiles_cache:
        profiles_cache["profiles"] = institution_profiles(db)
    text = " ".join(filter(None, [row.get("institution_name"), row.get("aicte_id"), row.get("institution_email"),
                                  row.get("institution_address")]))
    if not text.strip():
        return None, None
    res = resolve(profiles_cache["profiles"], text=text, top_k=3)
    return res, (res["candidates"][0] if res["candidates"] else None)


def _validate_case_row(row: dict, row_num: int, db: Session, profiles_cache: Optional[dict] = None) -> tuple:
    errors, warnings = [], []
    profiles_cache = profiles_cache if profiles_cache is not None else {}
    if not row.get("title", "").strip():
        errors.append("title is required")
    if not row.get("category", "").strip():
        errors.append("category is required")
    inst_id = row.get("institution_id")
    if not inst_id:
        res, top = _resolve_row_institution(row, db, profiles_cache)
        if res is None:
            errors.append("institution_id or institution_name is required")
        elif top and res["decision"] == "auto_link_suggested":
            row["institution_id"] = str(top["institution_id"])
            warnings.append(f"Institution resolved by IRE → {top['canonical_name']} ({int(top['confidence'] * 100)}%)")
        elif top:
            errors.append(f"Institution ambiguous — best guess {top['canonical_name']} ({int(top['confidence'] * 100)}%); add institution_id")
        else:
            errors.append("Institution could not be resolved from the registry")
    else:
        try:
            inst = db.query(Institution).filter(Institution.id == int(inst_id)).first()
            if not inst:
                errors.append(f"institution_id {inst_id} not found")
        except ValueError:
            errors.append("institution_id must be a number")
    priority = row.get("priority", "medium")
    if priority not in [p.value for p in CasePriority]:
        warnings.append(f"priority '{priority}' unknown, will default to 'medium'")
    return errors, warnings


async def _parse_csv(file: UploadFile) -> list:
    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


@router.post("/institutions/preview")
async def preview_institutions(
    file: UploadFile = File(...),
    current_user: User = Depends(
        require_roles(UserRole.DATA_ADMIN, UserRole.SYSTEM_ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """Validate institution CSV and return preview. Does NOT commit any data."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files accepted")

    try:
        rows = await _parse_csv(file)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV parse error: {e}")

    if not rows:
        raise HTTPException(status_code=422, detail="CSV file is empty")

    # Create job record
    job = ImportJob(
        filename=file.filename or "upload.csv",
        import_type="institutions",
        status=ImportStatus.PREVIEW,
        total_rows=len(rows),
        imported_by_id=current_user.id,
    )
    db.add(job)
    db.flush()

    preview_rows, valid_count, error_count = [], 0, 0
    for i, row in enumerate(rows, 1):
        errors, warnings = _validate_institution_row(row, i)
        
        # Check duplicate by canonical_name
        if row.get("canonical_name"):
            exists = db.query(Institution).filter(
                Institution.canonical_name == row["canonical_name"].strip()
            ).first()
            if exists:
                warnings.append(f"Institution '{row['canonical_name']}' already exists (id={exists.id}), will skip")

        ir = ImportRow(
            job_id=job.id,
            row_number=i,
            raw_data=row,
            status="valid" if not errors else "error",
            errors=errors or None,
            warnings=warnings or None,
        )
        db.add(ir)
        if errors:
            error_count += 1
        else:
            valid_count += 1

        preview_rows.append({
            "row": i,
            "data": row,
            "status": "valid" if not errors else "error",
            "errors": errors,
            "warnings": warnings,
        })

    job.valid_rows = valid_count
    job.error_rows = error_count
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Preview failed")

    return {
        "job_id": job.id,
        "total_rows": len(rows),
        "valid_rows": valid_count,
        "error_rows": error_count,
        "preview_rows": preview_rows[:50],  # Cap preview at 50 rows
        "message": f"Preview complete. {valid_count} valid rows, {error_count} errors."
    }


@router.post("/institutions/commit/{job_id}")
async def commit_institutions(
    job_id: int,
    current_user: User = Depends(
        require_roles(UserRole.DATA_ADMIN, UserRole.SYSTEM_ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """Commit a previously previewed import job."""
    job = db.query(ImportJob).filter(ImportJob.id == job_id, ImportJob.import_type == "institutions").first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status not in [ImportStatus.PREVIEW, ImportStatus.PENDING]:
        raise HTTPException(status_code=422, detail=f"Job is in status {job.status.value}, cannot commit")

    job.status = ImportStatus.IMPORTING
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    valid_rows = db.query(ImportRow).filter(ImportRow.job_id == job_id, ImportRow.status == "valid").all()
    imported, skipped = 0, 0

    for row in valid_rows:
        data = row.raw_data or {}
        name = data.get("canonical_name", "").strip()
        existing = db.query(Institution).filter(Institution.canonical_name == name).first()
        if existing:
            row.status = "skipped"
            skipped += 1
            continue
        try:
            inst = Institution(
                canonical_name=name,
                short_name=data.get("short_name"),
                institution_type=data.get("institution_type"),
                state=data.get("state"),
                district=data.get("district"),
                city=data.get("city"),
                region=data.get("region"),
                phone=data.get("phone"),
                email=data.get("email"),
                website=data.get("website"),
                data_source=f"import_job_{job_id}",
                import_notes="DEMO IMPORT",
                created_by_id=current_user.id,
            )
            db.add(inst)
            db.flush()
            row.status = "imported"
            row.created_resource_id = inst.id
            imported += 1
        except Exception as e:
            row.status = "error"
            row.errors = [str(e)]
            skipped += 1

    job.imported_rows = imported
    job.skipped_rows = skipped
    job.status = ImportStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        job.status = ImportStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail="Import commit failed")

    log_audit(db, current_user.id, "import_committed", "import_job", job_id,
              f"Imported {imported}, skipped {skipped}")
    return {"message": "Import complete", "imported": imported, "skipped": skipped, "job_id": job_id}


@router.post("/cases/preview")
async def preview_cases(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.DATA_ADMIN, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """Validate cases CSV and return preview. Does NOT commit."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files accepted")
    try:
        rows = await _parse_csv(file)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV parse error: {e}")
    if not rows:
        raise HTTPException(status_code=422, detail="CSV is empty")

    job = ImportJob(filename=file.filename or "cases.csv", import_type="cases",
                    status=ImportStatus.PREVIEW, total_rows=len(rows), imported_by_id=current_user.id)
    db.add(job)
    db.flush()

    preview_rows, valid_count, error_count = [], 0, 0
    profiles_cache: dict = {}
    for i, row in enumerate(rows, 1):
        errors, warnings = _validate_case_row(row, i, db, profiles_cache)
        ir = ImportRow(job_id=job.id, row_number=i, raw_data=row,
                       status="valid" if not errors else "error",
                       errors=errors or None, warnings=warnings or None)
        db.add(ir)
        if errors:
            error_count += 1
        else:
            valid_count += 1
        preview_rows.append({"row": i, "data": row, "status": "valid" if not errors else "error",
                              "errors": errors, "warnings": warnings})

    job.valid_rows = valid_count
    job.error_rows = error_count
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Preview failed")
    return {"job_id": job.id, "total_rows": len(rows), "valid_rows": valid_count,
            "error_rows": error_count, "preview_rows": preview_rows[:50]}


def _bureau_id(db: Session, code: Optional[str]) -> Optional[int]:
    if not code:
        return None
    from app.models.bureau import Bureau
    b = db.query(Bureau).filter(Bureau.code == code.strip().upper()).first()
    return b.id if b else None


def _parse_date(value: Optional[str]):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


@router.post("/cases/commit/{job_id}")
async def commit_cases(
    job_id: int,
    current_user: User = Depends(require_roles(UserRole.DATA_ADMIN, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc
    job = db.query(ImportJob).filter(ImportJob.id == job_id, ImportJob.import_type == "cases").first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status not in [ImportStatus.PREVIEW, ImportStatus.PENDING]:
        raise HTTPException(status_code=422, detail=f"Cannot commit job in status {job.status.value}")

    job.status = ImportStatus.IMPORTING
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    valid_rows = db.query(ImportRow).filter(ImportRow.job_id == job_id, ImportRow.status == "valid").all()
    imported, skipped = 0, 0
    year = datetime.now(timezone.utc).year

    for row in valid_rows:
        data = row.raw_data or {}
        try:
            count = db.query(sqlfunc.count(Case.id)).scalar() or 0
            case_num = f"AICTE-NS-{year}-{count + 1:05d}"
            priority_val = data.get("priority", "medium")
            try:
                priority = CasePriority(priority_val)
            except ValueError:
                priority = CasePriority.MEDIUM
            case = Case(
                case_number=case_num,
                title=data.get("title", "").strip(),
                summary=data.get("summary"),
                category=data.get("category", "").strip(),
                priority=priority,
                institution_id=int(data["institution_id"]),
                status=CaseStatus.RECEIVED,
                source_case_id=data.get("source_case_id"),
                source_system=data.get("source_system") or "CSV import",
                bureau_id=_bureau_id(db, data.get("bureau_code")),
                complainant_name=data.get("complainant_name"),
                received_date=_parse_date(data.get("received_date")) or datetime.now(timezone.utc),
                import_job_id=job_id,
                created_by_id=current_user.id,
            )
            db.add(case)
            db.flush()
            row.status = "imported"
            row.created_resource_id = case.id
            imported += 1
        except Exception as e:
            row.status = "error"
            row.errors = [str(e)]
            skipped += 1

    job.imported_rows = imported
    job.skipped_rows = skipped
    job.status = ImportStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        job.status = ImportStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail="Commit failed")
    return {"message": "Import complete", "imported": imported, "skipped": skipped}


@router.get("/", response_model=List[ImportJobOut])
async def list_imports(
    skip: int = 0, limit: int = 50,
    current_user: User = Depends(require_roles(UserRole.DATA_ADMIN, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    jobs = db.query(ImportJob).order_by(ImportJob.created_at.desc()).offset(skip).limit(limit).all()
    return jobs


@router.get("/{job_id}")
async def get_import(
    job_id: int,
    current_user: User = Depends(require_roles(UserRole.DATA_ADMIN, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    rows = db.query(ImportRow).filter(ImportRow.job_id == job_id).order_by(ImportRow.row_number).all()
    return {
        "id": job.id, "filename": job.filename, "import_type": job.import_type,
        "status": job.status.value, "total_rows": job.total_rows,
        "valid_rows": job.valid_rows, "error_rows": job.error_rows,
        "imported_rows": job.imported_rows, "created_at": job.created_at,
        "completed_at": job.completed_at,
        "rows": [{"row_number": r.row_number, "status": r.status,
                  "errors": r.errors, "warnings": r.warnings} for r in rows[:100]]
    }
