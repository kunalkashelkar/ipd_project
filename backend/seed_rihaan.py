import os
import sys
import uuid
from datetime import datetime, timedelta
import random
import asyncio

# Add parent directory to path to import backend modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from passlib.context import CryptContext

from backend.app.database.session import async_session_factory
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.scan import Scan
from backend.app.models.scan_result import ScanResult 
from backend.app.models.report import Report
# --------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_demo_user():
    async with async_session_factory() as db:
        try:
            # 1. Create Rihaan's User Account
            email = "itsrihaan28@gmail.com"
            password = "Aadi@282006"
            
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                hashed_password = pwd_context.hash(password)
                user = User(
                    id=uuid.uuid4(),
                    name="Rihaan",
                    email=email,
                    password_hash=hashed_password,
                    role="researcher",
                    created_at=datetime.utcnow()
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                print(f"✅ Created user: {email}")
            else:
                print(f"ℹ️ User {email} already exists. Using existing ID.")

            # 2. Define Historical Projects & Scans (The "Fake" Past)
            projects_data = [
                {
                    "name": "FinTech Payment Gateway", "lang": "Java", "desc": "Core transaction API",
                    "days_ago": 15,
                    "vulns": [
                        {"severity": "Critical", "cwe": "CWE-89", "cvss": 9.8, "file": "PaymentDAO.java", "func": "executeTransaction"},
                        {"severity": "High", "cwe": "CWE-611", "cvss": 7.5, "file": "XmlParser.java", "func": "parsePayload"},
                        {"severity": "Medium", "cwe": "CWE-327", "cvss": 5.3, "file": "CryptoUtils.java", "func": "encryptData"},
                    ]
                },
                {
                    "name": "E-Commerce Storefront", "lang": "JavaScript", "desc": "Next.js frontend & BFF",
                    "days_ago": 7,
                    "vulns": [
                        {"severity": "High", "cwe": "CWE-79", "cvss": 8.1, "file": "SearchBar.jsx", "func": "renderQuery"},
                        {"severity": "High", "cwe": "CWE-352", "cvss": 8.8, "file": "CheckoutAPI.js", "func": "processOrder"},
                        {"severity": "Low", "cwe": "CWE-1004", "cvss": 2.1, "file": "sessionConfig.js", "func": "setCookie"},
                        {"severity": "Medium", "cwe": "CWE-200", "cvss": 5.0, "file": "ErrorBoundary.jsx", "func": "logError"},
                    ]
                },
                {
                    "name": "Legacy CRM System", "lang": "Python", "desc": "Internal customer tool",
                    "days_ago": 2,
                    "vulns": [
                        {"severity": "Critical", "cwe": "CWE-78", "cvss": 9.8, "file": "report_generator.py", "func": "export_csv"},
                        {"severity": "High", "cwe": "CWE-22", "cvss": 7.5, "file": "file_upload.py", "func": "save_attachment"},
                        {"severity": "Medium", "cwe": "CWE-862", "cvss": 6.5, "file": "admin_routes.py", "func": "delete_user"},
                        {"severity": "Critical", "cwe": "CWE-502", "cvss": 9.1, "file": "pickle_loader.py", "func": "load_cache"},
                    ]
                }
            ]

            for p_data in projects_data:
                project = Project(
                    id=uuid.uuid4(), name=p_data["name"], language=p_data["lang"],
                    description=p_data["desc"], owner_id=user.id,
                    created_at=datetime.utcnow() - timedelta(days=p_data["days_ago"])
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)

                scan_date = datetime.utcnow() - timedelta(days=p_data["days_ago"]) + timedelta(hours=2)
                scan = Scan(
                    id=uuid.uuid4(), project_id=project.id, created_by=user.id,
                    status="completed", progress=100, started_at=scan_date,
                    completed_at=scan_date + timedelta(minutes=5), created_at=scan_date
                )
                db.add(scan)
                await db.commit()
                await db.refresh(scan)

                for v in p_data["vulns"]:
                    result = ScanResult(
                        id=uuid.uuid4(), scan_id=scan.id, severity=v["severity"].upper(),
                        cwe_id=v["cwe"], cvss_score=v["cvss"], file_path=v["file"],
                        function_name=v["func"], line_number=random.randint(10, 500),
                        confidence=round(random.uniform(0.85, 0.99), 2),
                        explanation=f"AI detected a {v['cwe']} vulnerability in {v['func']} due to unsafe handling of inputs.",
                        recommended_patch="Apply input validation and use secure, parameterized APIs.",
                        created_at=scan_date + timedelta(minutes=4)
                    )
                    db.add(result)

                report = Report(
                    id=uuid.uuid4(), scan_id=scan.id, format="pdf", status="completed",
                    generated_at=scan_date + timedelta(minutes=6), created_at=scan_date + timedelta(minutes=6)
                )
                db.add(report)
                print(f"📊 Seeded '{p_data['name']}' with {len(p_data['vulns'])} vulnerabilities.")

            await db.commit()
            print("\n🎉 SUCCESS! Rihaan's dashboard is now fully populated.")

        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(seed_demo_user())
