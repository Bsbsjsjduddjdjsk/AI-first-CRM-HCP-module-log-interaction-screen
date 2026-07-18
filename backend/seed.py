"""Run with: python seed.py -- populates a couple of reps, HCPs, and products
so the chat/form flows have something real to resolve against."""
from app.database import SessionLocal, engine, Base
from app import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(models.Rep).first():
    rep = models.Rep(name="Asha Verma", email="asha.verma@example.com", territory="South Zone")
    db.add(rep)

    hcps = [
        models.HCP(full_name="Dr. Priya Sharma", specialty="Cardiology",
                   institution="City Hospital", tier="A", consent_status=True),
        models.HCP(full_name="Dr. Rohan Rao", specialty="Endocrinology",
                   institution="Apollo Clinic", tier="B", consent_status=True),
    ]
    db.add_all(hcps)

    products = [
        models.Product(name="CardioX", approved_claims=["Reduces LDL cholesterol by up to 30%"]),
        models.Product(name="GlucoBalance", approved_claims=["Improves HbA1c control"]),
    ]
    db.add_all(products)

    db.commit()
    print("Seeded reps, HCPs, and products.")
else:
    print("Data already present, skipping seed.")

db.close()
