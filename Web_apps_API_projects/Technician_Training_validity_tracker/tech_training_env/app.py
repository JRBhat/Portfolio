"""
Technician Training Dates and Validity Tracking System
FastAPI + SQLite + Minimal HTML/CSS Interface
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from datetime import date, timedelta
import os

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./training_tracker.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    validity_days = Column(Integer)
    trainings = relationship("Training", back_populates="device")

class Technician(Base):
    __tablename__ = "technicians"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    trainings = relationship("Training", back_populates="technician")

class Training(Base):
    __tablename__ = "trainings"
    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"))
    device_id = Column(Integer, ForeignKey("devices.id"))
    training_date = Column(Date)
    valid_until = Column(Date)
    technician = relationship("Technician", back_populates="trainings")
    device = relationship("Device", back_populates="trainings")

Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="Technician Training Tracker")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Simple admin password (in production, use proper authentication)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

def verify_admin(password: str):
    return password == ADMIN_PASSWORD

# HTML Templates (inline for simplicity)
HTML_BASE = """
<!DOCTYPE html>
<html>
<head>
    <title>Training Tracker</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; margin-bottom: 20px; }}
        .nav {{ margin-bottom: 30px; padding-bottom: 15px; border-bottom: 2px solid #eee; }}
        .nav a {{ margin-right: 15px; text-decoration: none; color: #007bff; }}
        .nav a:hover {{ text-decoration: underline; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; color: #555; }}
        input, select {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }}
        button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }}
        button:hover {{ background: #0056b3; }}
        .delete-btn {{ background: #dc3545; }}
        .delete-btn:hover {{ background: #c82333; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        .valid {{ color: green; font-weight: bold; }}
        .expired {{ color: red; font-weight: bold; }}
        .message {{ padding: 10px; margin-bottom: 20px; border-radius: 4px; }}
        .success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""

# Routes
@app.get("/", response_class=HTMLResponse)
def home():
    content = """
    <h1>Technician Training Tracker</h1>
    <div class="nav">
        <a href="/user">User Mode</a>
        <a href="/admin">Admin Mode</a>
    </div>
    <p>Welcome! Please select a mode:</p>
    <ul style="margin-top: 15px; margin-left: 20px;">
        <li style="margin-bottom: 10px;"><strong>User Mode:</strong> Record your training dates</li>
        <li><strong>Admin Mode:</strong> Manage devices and view all records</li>
    </ul>
    """
    return HTML_BASE.format(content=content)

@app.get("/user", response_class=HTMLResponse)
def user_page(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    technicians = db.query(Technician).all()
    
    device_options = "".join([f'<option value="{d.id}">{d.name} ({d.validity_days} days)</option>' for d in devices])
    tech_options = "".join([f'<option value="{t.id}">{t.name}</option>' for t in technicians])
    
    content = f"""
    <h1>User Mode - Record Training</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/user/view">View My Trainings</a>
    </div>
    
    <form method="post" action="/user/submit">
        <div class="form-group">
            <label>Technician Name:</label>
            <select name="technician_id">
                <option value="">Select or add new below</option>
                {tech_options}
            </select>
        </div>
        
        <div class="form-group">
            <label>Or Enter New Name:</label>
            <input type="text" name="new_technician" placeholder="Leave blank if selected above">
        </div>
        
        <div class="form-group">
            <label>Device:</label>
            <select name="device_id" required>
                <option value="">Select a device</option>
                {device_options}
            </select>
        </div>
        
        <div class="form-group">
            <label>Training Date:</label>
            <input type="date" name="training_date" value="{date.today()}" required>
        </div>
        
        <button type="submit">Submit Training</button>
    </form>
    """
    return HTML_BASE.format(content=content)

@app.post("/user/submit")
def submit_training(
    technician_id: str | None = Form(None),
    new_technician: str = Form(""),
    device_id: int = Form(...),
    training_date: date = Form(...),
    db: Session = Depends(get_db)
):
    # Get or create technician
    if new_technician.strip():
        tech = db.query(Technician).filter(Technician.name == new_technician.strip()).first()
        if not tech:
            tech = Technician(name=new_technician.strip())
            db.add(tech)
            db.commit()
            db.refresh(tech)
    elif technician_id and technician_id.strip():
        tech = db.query(Technician).filter(Technician.id == int(technician_id)).first()
    else:
        raise HTTPException(status_code=400, detail="Please select or enter a technician name")
    
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    valid_until = training_date + timedelta(days=device.validity_days)
    
    training = Training(
        technician_id=tech.id,
        device_id=device_id,
        training_date=training_date,
        valid_until=valid_until
    )
    db.add(training)
    db.commit()
    
    return RedirectResponse(url="/user/view?msg=success", status_code=303)

@app.get("/user/view", response_class=HTMLResponse)
def view_trainings(msg: str | None = None, db: Session = Depends(get_db)):
    technicians = db.query(Technician).all()
    tech_options = "".join([f'<option value="{t.id}">{t.name}</option>' for t in technicians])
    
    message = ""
    if msg == "success":
        message = '<div class="message success">Training recorded successfully!</div>'
    
    content = f"""
    <h1>View Trainings</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/user">Record Training</a>
    </div>
    
    {message}
    
    <form method="get" action="/user/trainings">
        <div class="form-group">
            <label>Select Technician:</label>
            <select name="tech_id" required>
                <option value="">Select a technician</option>
                {tech_options}
            </select>
        </div>
        <button type="submit">View Trainings</button>
    </form>
    """
    return HTML_BASE.format(content=content)

@app.get("/user/trainings", response_class=HTMLResponse)
def get_trainings(tech_id: int, db: Session = Depends(get_db)):
    tech = db.query(Technician).filter(Technician.id == tech_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    trainings = db.query(Training).filter(Training.technician_id == tech_id).all()
    
    rows = ""
    for t in trainings:
        status_class = "valid" if t.valid_until >= date.today() else "expired"
        status_text = "VALID" if t.valid_until >= date.today() else "EXPIRED"
        rows += f"""
        <tr>
            <td>{t.device.name}</td>
            <td>{t.training_date}</td>
            <td>{t.valid_until}</td>
            <td class="{status_class}">{status_text}</td>
        </tr>
        """
    
    content = f"""
    <h1>Trainings for {tech.name}</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/user">Record Training</a>
        <a href="/user/view">Back</a>
    </div>
    
    <table>
        <tr>
            <th>Device</th>
            <th>Training Date</th>
            <th>Valid Until</th>
            <th>Status</th>
        </tr>
        {rows if rows else '<tr><td colspan="4" style="text-align: center;">No trainings recorded</td></tr>'}
    </table>
    """
    return HTML_BASE.format(content=content)

@app.get("/admin", response_class=HTMLResponse)
def admin_login():
    content = """
    <h1>Admin Mode</h1>
    <div class="nav">
        <a href="/">Home</a>
    </div>
    
    <form method="post" action="/admin/login">
        <div class="form-group">
            <label>Admin Password:</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit">Login</button>
    </form>
    
    <p style="margin-top: 20px; color: #666; font-size: 12px;">Default password: admin123</p>
    """
    return HTML_BASE.format(content=content)

@app.post("/admin/login")
def admin_login_submit(password: str = Form(...)):
    if verify_admin(password):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return RedirectResponse(url="/admin?error=1", status_code=303)

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    
    device_rows = ""
    for d in devices:
        device_rows += f"""
        <tr>
            <td>{d.name}</td>
            <td>{d.validity_days}</td>
            <td>
                <form method="post" action="/admin/device/delete/{d.id}" style="display: inline;">
                    <button type="submit" class="delete-btn" onclick="return confirm('Delete this device?')">Delete</button>
                </form>
            </td>
        </tr>
        """
    
    content = f"""
    <h1>Admin Dashboard</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/admin/all-trainings">View All Trainings</a>
    </div>
    
    <h2>Add New Device</h2>
    <form method="post" action="/admin/device/add">
        <div class="form-group">
            <label>Device Name:</label>
            <input type="text" name="name" required>
        </div>
        <div class="form-group">
            <label>Validity Period (days):</label>
            <input type="number" name="validity_days" min="1" required>
        </div>
        <button type="submit">Add Device</button>
    </form>
    
    <h2 style="margin-top: 30px;">Existing Devices</h2>
    <table>
        <tr>
            <th>Device Name</th>
            <th>Validity (days)</th>
            <th>Actions</th>
        </tr>
        {device_rows if device_rows else '<tr><td colspan="3" style="text-align: center;">No devices added</td></tr>'}
    </table>
    """
    return HTML_BASE.format(content=content)

@app.post("/admin/device/add")
def add_device(name: str = Form(...), validity_days: int = Form(...), db: Session = Depends(get_db)):
    device = Device(name=name, validity_days=validity_days)
    db.add(device)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@app.post("/admin/device/delete/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if device:
        db.delete(device)
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@app.get("/admin/all-trainings", response_class=HTMLResponse)
def all_trainings(db: Session = Depends(get_db)):
    trainings = db.query(Training).all()
    
    rows = ""
    for t in trainings:
        status_class = "valid" if t.valid_until >= date.today() else "expired"
        status_text = "VALID" if t.valid_until >= date.today() else "EXPIRED"
        rows += f"""
        <tr>
            <td>{t.technician.name}</td>
            <td>{t.device.name}</td>
            <td>{t.training_date}</td>
            <td>{t.valid_until}</td>
            <td class="{status_class}">{status_text}</td>
        </tr>
        """
    
    content = f"""
    <h1>All Training Records</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/admin/dashboard">Admin Dashboard</a>
    </div>
    
    <table>
        <tr>
            <th>Technician</th>
            <th>Device</th>
            <th>Training Date</th>
            <th>Valid Until</th>
            <th>Status</th>
        </tr>
        {rows if rows else '<tr><td colspan="5" style="text-align: center;">No training records</td></tr>'}
    </table>
    """
    return HTML_BASE.format(content=content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)