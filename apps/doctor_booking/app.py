"""
MediBook — Doctor Appointment Booking Demo App
Port 5002 | Login: patient@medibook.com / HealthPass123!

3 planted bugs:
  1. Double booking — same doctor/date/slot can be booked multiple times (no conflict check)
  2. IDOR on cancel — /cancel/<id> cancels any appointment regardless of who owns it
  3. Vague confirmation — booking success page shows no doctor name, date, time, or reference number
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import os

app = Flask(__name__)
app.secret_key = "medibook-demo-secret-key-2024"

USERS = {
    "patient@medibook.com": {"password": "HealthPass123!", "name": "Alex Johnson"},
    "sam@medibook.com":     {"password": "HealthPass123!", "name": "Sam Williams"},
}

DOCTORS = {
    "d1": {
        "id": "d1",
        "name": "Dr. Sarah Chen",
        "specialty": "Cardiologist",
        "hospital": "Mount Sinai Medical Center",
        "rating": 4.9,
        "reviews": 312,
        "experience": "18 years",
        "fee": 250,
        "initials": "SC",
        "color": "#0d9488",
        "education": "MD, Johns Hopkins University",
        "languages": "English, Mandarin",
        "about": "Dr. Chen specializes in interventional cardiology and has performed over 2,000 cardiac procedures. She is board-certified and a Fellow of the American College of Cardiology.",
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM", "4:00 PM"],
    },
    "d2": {
        "id": "d2",
        "name": "Dr. James Okafor",
        "specialty": "Dermatologist",
        "hospital": "NYU Langone Health",
        "rating": 4.7,
        "reviews": 198,
        "experience": "12 years",
        "fee": 180,
        "initials": "JO",
        "color": "#7c3aed",
        "education": "MD, Columbia University",
        "languages": "English, Yoruba",
        "about": "Dr. Okafor is a board-certified dermatologist specializing in medical, surgical, and cosmetic dermatology. He has a particular interest in skin conditions affecting patients of color.",
        "slots": ["8:30 AM", "9:30 AM", "11:30 AM", "1:00 PM", "2:30 PM", "5:00 PM"],
    },
    "d3": {
        "id": "d3",
        "name": "Dr. Priya Menon",
        "specialty": "Neurologist",
        "hospital": "Cleveland Clinic",
        "rating": 4.8,
        "reviews": 445,
        "experience": "22 years",
        "fee": 300,
        "initials": "PM",
        "color": "#dc2626",
        "education": "MD, AIIMS New Delhi; Fellowship, Mayo Clinic",
        "languages": "English, Hindi, Malayalam",
        "about": "Dr. Menon is a renowned neurologist with expertise in epilepsy, movement disorders, and neurodegenerative diseases. She leads the Epilepsy Center at Cleveland Clinic.",
        "slots": ["10:00 AM", "11:00 AM", "1:00 PM", "3:00 PM", "4:30 PM"],
    },
    "d4": {
        "id": "d4",
        "name": "Dr. Michael Torres",
        "specialty": "Orthopedic Surgeon",
        "hospital": "Hospital for Special Surgery",
        "rating": 4.6,
        "reviews": 267,
        "experience": "15 years",
        "fee": 220,
        "initials": "MT",
        "color": "#ea580c",
        "education": "MD, Stanford University School of Medicine",
        "languages": "English, Spanish",
        "about": "Dr. Torres specializes in sports medicine and minimally invasive joint replacement surgery. He is the team physician for two professional sports teams.",
        "slots": ["8:00 AM", "9:00 AM", "10:30 AM", "12:00 PM", "2:00 PM", "3:30 PM"],
    },
    "d5": {
        "id": "d5",
        "name": "Dr. Aisha Rahman",
        "specialty": "Pediatrician",
        "hospital": "Children's Hospital of Philadelphia",
        "rating": 4.9,
        "reviews": 521,
        "experience": "10 years",
        "fee": 150,
        "initials": "AR",
        "color": "#0284c7",
        "education": "MD, Harvard Medical School",
        "languages": "English, Arabic, French",
        "about": "Dr. Rahman is a compassionate pediatrician dedicated to the health and wellbeing of children from birth through adolescence. She specializes in developmental pediatrics.",
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM"],
    },
    "d6": {
        "id": "d6",
        "name": "Dr. Robert Kim",
        "specialty": "Psychiatrist",
        "hospital": "Massachusetts General Hospital",
        "rating": 4.8,
        "reviews": 189,
        "experience": "20 years",
        "fee": 280,
        "initials": "RK",
        "color": "#0f766e",
        "education": "MD, Yale School of Medicine",
        "languages": "English, Korean",
        "about": "Dr. Kim is a board-certified psychiatrist specializing in mood disorders, anxiety, and trauma. He combines evidence-based pharmacotherapy with psychotherapy approaches.",
        "slots": ["10:00 AM", "11:00 AM", "12:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"],
    },
}

# All appointments across all patients: appt_id -> appt dict
_appointments: dict = {}
_appt_counter = [100]


def logged_in():
    return "email" in session


# ── Templates ─────────────────────────────────────────────────────────────────

BASE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}MediBook{% endblock %} — Find & Book Doctors</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
  <style>
    :root { --teal: #0d9488; --teal-dark: #0f766e; --teal-light: #ccfbf1; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f8fafc; }
    .navbar-brand { font-weight: 700; font-size: 1.4rem; color: #fff !important; }
    .navbar-brand span { color: #5eead4; }
    .nav-link { color: rgba(255,255,255,.85) !important; }
    .nav-link:hover { color: #fff !important; }
    .hero { background: linear-gradient(135deg, #0f766e 0%, #0d9488 50%, #14b8a6 100%); color: #fff; padding: 64px 0 48px; }
    .doctor-card { border: none; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,.08); transition: transform .2s, box-shadow .2s; }
    .doctor-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,.12); }
    .avatar { width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; color: #fff; flex-shrink: 0; }
    .avatar-lg { width: 88px; height: 88px; font-size: 1.6rem; }
    .rating-badge { background: #fef3c7; color: #92400e; border-radius: 20px; padding: 2px 10px; font-size: .82rem; font-weight: 600; }
    .specialty-badge { background: var(--teal-light); color: var(--teal-dark); border-radius: 20px; padding: 3px 12px; font-size: .82rem; font-weight: 600; }
    .slot-btn { border: 2px solid #e2e8f0; border-radius: 8px; padding: 8px 16px; font-size: .88rem; cursor: pointer; background: #fff; transition: all .15s; display: inline-block; }
    .slot-btn:hover, .slot-btn.selected { border-color: var(--teal); background: var(--teal-light); color: var(--teal-dark); }
    .appt-card { border-left: 4px solid var(--teal); border-radius: 8px; background: #fff; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 12px; }
    .appt-card.cancelled { border-color: #ef4444; opacity: .65; }
    .btn-teal { background: var(--teal); border-color: var(--teal); color: #fff; }
    .btn-teal:hover { background: var(--teal-dark); border-color: var(--teal-dark); color: #fff; }
    .btn-outline-teal { border-color: var(--teal); color: var(--teal); }
    .btn-outline-teal:hover { background: var(--teal); color: #fff; }
    .text-teal { color: var(--teal) !important; }
    .search-bar { border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,.15); overflow: hidden; }
    .search-bar input, .search-bar select { border: none; padding: 14px 18px; font-size: 1rem; }
    .search-bar input:focus, .search-bar select:focus { box-shadow: none; }
    .search-bar button { border-radius: 0; padding: 14px 28px; }
    footer { background: #1e293b; color: #94a3b8; padding: 40px 0 24px; }
    footer a { color: #94a3b8; text-decoration: none; }
    footer a:hover { color: #fff; }
  </style>
</head>
<body>
<nav class="navbar navbar-expand-lg" style="background: var(--teal-dark);">
  <div class="container">
    <a class="navbar-brand" href="/"><i class="fa-solid fa-stethoscope me-2"></i>Medi<span>Book</span></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="nav">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="/"><i class="fa-solid fa-house me-1"></i>Home</a></li>
        <li class="nav-item"><a class="nav-link" href="/doctors"><i class="fa-solid fa-user-doctor me-1"></i>Doctors</a></li>
        {% if session.get('email') %}
        <li class="nav-item"><a class="nav-link" href="/appointments"><i class="fa-solid fa-calendar-check me-1"></i>My Appointments</a></li>
        {% endif %}
      </ul>
      <ul class="navbar-nav">
        {% if session.get('email') %}
        <li class="nav-item dropdown">
          <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
            <i class="fa-solid fa-circle-user me-1"></i>{{ session.get('name', 'Patient') }}
          </a>
          <ul class="dropdown-menu dropdown-menu-end">
            <li><a class="dropdown-item" href="/appointments">My Appointments</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item text-danger" href="/logout">Logout</a></li>
          </ul>
        </li>
        {% else %}
        <li class="nav-item"><a class="nav-link" href="/login">Login</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
  <div class="container mt-3">
    {% for category, message in messages %}
    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show">
      {{ message }}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    {% endfor %}
  </div>
  {% endif %}
{% endwith %}

{% block content %}{% endblock %}

<footer>
  <div class="container">
    <div class="row g-4 mb-4">
      <div class="col-md-4">
        <h5 class="text-white mb-3"><i class="fa-solid fa-stethoscope me-2"></i>MediBook</h5>
        <p style="font-size:.9rem;">Connecting patients with the best healthcare providers. Book appointments online in minutes.</p>
      </div>
      <div class="col-md-2">
        <h6 class="text-white mb-3">Specialties</h6>
        <ul class="list-unstyled" style="font-size:.9rem;">
          <li><a href="#">Cardiology</a></li>
          <li><a href="#">Dermatology</a></li>
          <li><a href="#">Neurology</a></li>
          <li><a href="#">Pediatrics</a></li>
        </ul>
      </div>
      <div class="col-md-2">
        <h6 class="text-white mb-3">Company</h6>
        <ul class="list-unstyled" style="font-size:.9rem;">
          <li><a href="#">About Us</a></li>
          <li><a href="#">Careers</a></li>
          <li><a href="#">Blog</a></li>
          <li><a href="#">Press</a></li>
        </ul>
      </div>
      <div class="col-md-2">
        <h6 class="text-white mb-3">Support</h6>
        <ul class="list-unstyled" style="font-size:.9rem;">
          <li><a href="#">Help Center</a></li>
          <li><a href="#">Contact Us</a></li>
          <li><a href="#">Privacy Policy</a></li>
          <li><a href="#">Terms of Service</a></li>
        </ul>
      </div>
      <div class="col-md-2">
        <h6 class="text-white mb-3">Follow Us</h6>
        <div class="d-flex gap-3" style="font-size:1.3rem;">
          <a href="#"><i class="fab fa-twitter"></i></a>
          <a href="#"><i class="fab fa-linkedin"></i></a>
          <a href="#"><i class="fab fa-instagram"></i></a>
        </div>
      </div>
    </div>
    <hr style="border-color:#334155;">
    <div class="d-flex justify-content-between align-items-center" style="font-size:.85rem;">
      <span>© 2024 MediBook Inc. All rights reserved.</span>
      <span><i class="fa-solid fa-shield-halved me-1"></i>HIPAA Compliant &nbsp;|&nbsp; <i class="fa-solid fa-lock me-1"></i>SSL Secured</span>
    </div>
  </div>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
{% block scripts %}{% endblock %}
</body>
</html>"""


HOME_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="hero">
  <div class="container text-center">
    <h1 class="fw-bold mb-3" style="font-size:2.6rem;">Find & Book Top Doctors</h1>
    <p class="mb-4" style="font-size:1.15rem; opacity:.9;">Connect with verified specialists. Same-day appointments available.</p>
    <form action="/doctors" method="get" class="d-flex search-bar bg-white mx-auto" style="max-width:680px;">
      <input class="form-control flex-grow-1" type="text" name="q" placeholder="Search by name or specialty...">
      <select class="form-select" name="specialty" style="max-width:180px; border-left:1px solid #e2e8f0;">
        <option value="">All Specialties</option>
        <option>Cardiologist</option>
        <option>Dermatologist</option>
        <option>Neurologist</option>
        <option>Orthopedic Surgeon</option>
        <option>Pediatrician</option>
        <option>Psychiatrist</option>
      </select>
      <button class="btn btn-teal px-4" type="submit"><i class="fa-solid fa-magnifying-glass me-2"></i>Search</button>
    </form>
    <div class="mt-4 d-flex justify-content-center gap-4" style="font-size:.9rem; opacity:.85;">
      <span><i class="fa-solid fa-circle-check me-1"></i>Verified Doctors</span>
      <span><i class="fa-solid fa-circle-check me-1"></i>Instant Booking</span>
      <span><i class="fa-solid fa-circle-check me-1"></i>Free Cancellation</span>
    </div>
  </div>
</div>

<div class="container py-5">
  <div class="row g-3 mb-5 text-center">
    <div class="col-6 col-md-3">
      <div class="bg-white rounded-3 p-4 shadow-sm">
        <div class="fw-bold text-teal" style="font-size:1.8rem;">10K+</div>
        <div class="text-muted" style="font-size:.9rem;">Verified Doctors</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="bg-white rounded-3 p-4 shadow-sm">
        <div class="fw-bold text-teal" style="font-size:1.8rem;">500K+</div>
        <div class="text-muted" style="font-size:.9rem;">Appointments Booked</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="bg-white rounded-3 p-4 shadow-sm">
        <div class="fw-bold text-teal" style="font-size:1.8rem;">50+</div>
        <div class="text-muted" style="font-size:.9rem;">Specialties</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="bg-white rounded-3 p-4 shadow-sm">
        <div class="fw-bold text-teal" style="font-size:1.8rem;">4.8★</div>
        <div class="text-muted" style="font-size:.9rem;">Average Rating</div>
      </div>
    </div>
  </div>

  <div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold mb-0">Featured Doctors</h2>
    <a href="/doctors" class="btn btn-outline-teal btn-sm">View All <i class="fa-solid fa-arrow-right ms-1"></i></a>
  </div>
  <div class="row g-4">
    {% for doc in featured %}
    <div class="col-md-6 col-lg-4">
      <div class="card doctor-card h-100">
        <div class="card-body p-4">
          <div class="d-flex align-items-start gap-3 mb-3">
            <div class="avatar" style="background:{{ doc.color }}">{{ doc.initials }}</div>
            <div>
              <h6 class="mb-1 fw-semibold">{{ doc.name }}</h6>
              <span class="specialty-badge">{{ doc.specialty }}</span>
            </div>
          </div>
          <p class="text-muted mb-1" style="font-size:.85rem;"><i class="fa-solid fa-hospital me-1"></i>{{ doc.hospital }}</p>
          <p class="text-muted mb-3" style="font-size:.85rem;"><i class="fa-solid fa-briefcase me-1"></i>{{ doc.experience }} experience</p>
          <div class="d-flex justify-content-between align-items-center">
            <span class="rating-badge"><i class="fa-solid fa-star me-1"></i>{{ doc.rating }} ({{ doc.reviews }})</span>
            <span class="fw-bold text-teal">${{ doc.fee }}</span>
          </div>
        </div>
        <div class="card-footer bg-transparent border-top-0 pb-4 px-4">
          <a href="/doctor/{{ doc.id }}" class="btn btn-teal w-100">Book Appointment</a>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
</div>

<div class="py-5" style="background:#f0fdfa;">
  <div class="container">
    <h2 class="fw-bold text-center mb-5">How MediBook Works</h2>
    <div class="row g-4 text-center">
      <div class="col-md-4">
        <div class="mb-3 text-teal" style="font-size:2.5rem;"><i class="fa-solid fa-magnifying-glass-plus"></i></div>
        <h5 class="fw-semibold">1. Find a Doctor</h5>
        <p class="text-muted">Search by specialty, location, or insurance. Read reviews and compare.</p>
      </div>
      <div class="col-md-4">
        <div class="mb-3 text-teal" style="font-size:2.5rem;"><i class="fa-solid fa-calendar-days"></i></div>
        <h5 class="fw-semibold">2. Book a Slot</h5>
        <p class="text-muted">Choose a time from real-time availability. Instant confirmation.</p>
      </div>
      <div class="col-md-4">
        <div class="mb-3 text-teal" style="font-size:2.5rem;"><i class="fa-solid fa-user-doctor"></i></div>
        <h5 class="fw-semibold">3. See Your Doctor</h5>
        <p class="text-muted">Visit in-person or connect via video from the comfort of home.</p>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")


DOCTORS_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5">
  <form action="/doctors" method="get" class="row g-3 mb-4 p-4 bg-white rounded-3 shadow-sm">
    <div class="col-md-5">
      <div class="input-group">
        <span class="input-group-text"><i class="fa-solid fa-magnifying-glass"></i></span>
        <input class="form-control" type="text" name="q" placeholder="Name or specialty..." value="{{ q }}">
      </div>
    </div>
    <div class="col-md-4">
      <select class="form-select" name="specialty">
        <option value="">All Specialties</option>
        {% for s in specialties %}
        <option value="{{ s }}" {% if specialty == s %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-3">
      <button class="btn btn-teal w-100" type="submit"><i class="fa-solid fa-filter me-2"></i>Filter</button>
    </div>
  </form>

  <h5 class="fw-semibold mb-3">{{ doctors|length }} doctors found</h5>
  <div class="row g-4">
    {% for doc in doctors %}
    <div class="col-md-6">
      <div class="card doctor-card">
        <div class="card-body p-4">
          <div class="d-flex gap-3">
            <div class="avatar avatar-lg" style="background:{{ doc.color }}">{{ doc.initials }}</div>
            <div class="flex-grow-1">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <h5 class="mb-1 fw-semibold">{{ doc.name }}</h5>
                  <span class="specialty-badge">{{ doc.specialty }}</span>
                </div>
                <span class="fw-bold text-teal fs-5">${{ doc.fee }}</span>
              </div>
              <p class="text-muted mt-2 mb-1" style="font-size:.88rem;"><i class="fa-solid fa-hospital me-1"></i>{{ doc.hospital }}</p>
              <p class="text-muted mb-2" style="font-size:.88rem;">
                <i class="fa-solid fa-briefcase me-1"></i>{{ doc.experience }}
                &nbsp;·&nbsp;
                <i class="fa-solid fa-globe me-1"></i>{{ doc.languages }}
              </p>
              <div class="d-flex align-items-center justify-content-between mt-3">
                <span class="rating-badge"><i class="fa-solid fa-star me-1"></i>{{ doc.rating }} · {{ doc.reviews }} reviews</span>
                <a href="/doctor/{{ doc.id }}" class="btn btn-teal btn-sm px-3">Book Now</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
    {% if not doctors %}
    <div class="col-12 text-center py-5">
      <i class="fa-solid fa-user-doctor fa-3x text-muted mb-3 d-block"></i>
      <h5 class="text-muted">No doctors found.</h5>
      <a href="/doctors" class="btn btn-outline-teal mt-2">Clear Filters</a>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}""")


DOCTOR_DETAIL_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5">
  <nav aria-label="breadcrumb" class="mb-4">
    <ol class="breadcrumb">
      <li class="breadcrumb-item"><a href="/" class="text-teal">Home</a></li>
      <li class="breadcrumb-item"><a href="/doctors" class="text-teal">Doctors</a></li>
      <li class="breadcrumb-item active">{{ doc.name }}</li>
    </ol>
  </nav>
  <div class="row g-4">
    <div class="col-lg-8">
      <div class="card border-0 shadow-sm rounded-3 mb-4">
        <div class="card-body p-4">
          <div class="d-flex gap-4 align-items-start">
            <div class="avatar avatar-lg" style="background:{{ doc.color }}">{{ doc.initials }}</div>
            <div class="flex-grow-1">
              <h3 class="fw-bold mb-1">{{ doc.name }}</h3>
              <div class="d-flex flex-wrap gap-2 mb-2">
                <span class="specialty-badge fs-6">{{ doc.specialty }}</span>
                <span class="badge bg-light text-dark fw-normal">{{ doc.experience }} exp.</span>
              </div>
              <p class="text-muted mb-1"><i class="fa-solid fa-hospital me-1 text-teal"></i>{{ doc.hospital }}</p>
              <p class="text-muted mb-1"><i class="fa-solid fa-graduation-cap me-1 text-teal"></i>{{ doc.education }}</p>
              <p class="text-muted mb-0"><i class="fa-solid fa-globe me-1 text-teal"></i>Speaks: {{ doc.languages }}</p>
            </div>
            <div class="text-end">
              <div class="rating-badge mb-2 d-inline-block"><i class="fa-solid fa-star me-1"></i>{{ doc.rating }}</div>
              <div class="text-muted" style="font-size:.85rem;">{{ doc.reviews }} reviews</div>
              <div class="fw-bold text-teal fs-4 mt-2">${{ doc.fee }}</div>
              <div class="text-muted" style="font-size:.8rem;">per visit</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card border-0 shadow-sm rounded-3 mb-4">
        <div class="card-body p-4">
          <h5 class="fw-semibold mb-3">About</h5>
          <p class="text-muted">{{ doc.about }}</p>
        </div>
      </div>

      <div class="card border-0 shadow-sm rounded-3">
        <div class="card-body p-4">
          <h5 class="fw-semibold mb-3">Patient Reviews</h5>
          {% for r in reviews %}
          <div class="border-bottom pb-3 mb-3">
            <div class="d-flex justify-content-between mb-1">
              <span class="fw-semibold">{{ r.name }}</span>
              <span class="rating-badge"><i class="fa-solid fa-star me-1"></i>{{ r.rating }}</span>
            </div>
            <p class="text-muted mb-0" style="font-size:.9rem;">{{ r.text }}</p>
          </div>
          {% endfor %}
        </div>
      </div>
    </div>

    <div class="col-lg-4">
      <div class="card border-0 shadow-sm rounded-3 sticky-top" style="top:80px;">
        <div class="card-body p-4">
          <h5 class="fw-semibold mb-3"><i class="fa-solid fa-calendar-plus me-2 text-teal"></i>Book Appointment</h5>
          {% if session.get('email') %}
          <form action="/book" method="post">
            <input type="hidden" name="doctor_id" value="{{ doc.id }}">
            <div class="mb-3">
              <label class="form-label fw-medium">Select Date</label>
              <input class="form-control" type="date" name="date" required min="{{ today }}" value="{{ today }}">
            </div>
            <div class="mb-3">
              <label class="form-label fw-medium">Available Slots</label>
              <div class="d-flex flex-wrap gap-2">
                {% for slot in doc.slots %}
                <label class="slot-btn" onclick="selectSlot(this)">
                  <input type="radio" name="slot" value="{{ slot }}" class="d-none" required> {{ slot }}
                </label>
                {% endfor %}
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label fw-medium">Reason for Visit</label>
              <input class="form-control" type="text" name="reason" placeholder="e.g. Annual checkup" required>
            </div>
            <div class="mb-3">
              <label class="form-label fw-medium">Patient Notes</label>
              <textarea class="form-control" name="patient_notes" rows="2" placeholder="Any symptoms or concerns..."></textarea>
            </div>
            <button type="submit" class="btn btn-teal w-100 py-2 fw-semibold">
              <i class="fa-solid fa-calendar-check me-2"></i>Confirm Booking — ${{ doc.fee }}
            </button>
          </form>
          {% else %}
          <div class="text-center py-3">
            <i class="fa-solid fa-lock fa-2x text-muted mb-3 d-block"></i>
            <p class="text-muted mb-3">Please login to book an appointment</p>
            <a href="/login" class="btn btn-teal w-100">Login to Book</a>
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>
<script>
function selectSlot(el) {
  document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
}
</script>
{% endblock %}""")


# BUG 3: Vague success — no doctor name, date, time, or reference number shown
BOOKING_SUCCESS_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5" style="max-width:560px;">
  <div class="card border-0 shadow-sm rounded-3 text-center p-5">
    <div class="mb-4 text-teal" style="font-size:3rem;"><i class="fa-solid fa-circle-check"></i></div>
    <h3 class="fw-bold mb-2">Booking Confirmed!</h3>
    <p class="text-muted mb-4">Your appointment has been successfully booked.</p>
    <p class="text-muted" style="font-size:.9rem;">Please check your email for further details.</p>
    <div class="d-flex gap-3 justify-content-center mt-3">
      <a href="/appointments" class="btn btn-teal px-4">View My Appointments</a>
      <a href="/doctors" class="btn btn-outline-secondary px-4">Find Another Doctor</a>
    </div>
  </div>
</div>
{% endblock %}""")


APPOINTMENTS_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5">
  <h2 class="fw-bold mb-4">My Appointments</h2>
  {% if appointments %}
  <div>
    {% for appt in appointments %}
    <div class="appt-card {{ 'cancelled' if appt.status == 'Cancelled' else '' }}">
      <div class="d-flex justify-content-between align-items-start">
        <div class="d-flex gap-3 align-items-start">
          <div class="avatar" style="background:{{ appt.doctor.color }}">{{ appt.doctor.initials }}</div>
          <div>
            <h6 class="fw-semibold mb-1">{{ appt.doctor.name }}</h6>
            <span class="specialty-badge" style="font-size:.78rem;">{{ appt.doctor.specialty }}</span>
            <div class="mt-2 text-muted" style="font-size:.88rem;">
              <i class="fa-solid fa-calendar me-1"></i>{{ appt.date }}
              &nbsp;·&nbsp;
              <i class="fa-solid fa-clock me-1"></i>{{ appt.slot }}
            </div>
            <div class="text-muted" style="font-size:.88rem;">
              <i class="fa-solid fa-clipboard-list me-1"></i>{{ appt.reason }}
            </div>
            <div class="text-muted" style="font-size:.85rem;">Ref #{{ appt.id }}</div>
          </div>
        </div>
        <div class="text-end">
          <span class="badge {{ 'bg-success' if appt.status == 'Confirmed' else 'bg-danger' }} mb-2">{{ appt.status }}</span>
          <div class="fw-bold text-teal">${{ appt.doctor.fee }}</div>
          {% if appt.status != 'Cancelled' %}
          <a href="/cancel/{{ appt.id }}" class="btn btn-outline-danger btn-sm mt-2"
             onclick="return confirm('Cancel this appointment?')">
            <i class="fa-solid fa-xmark me-1"></i>Cancel
          </a>
          {% endif %}
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <div class="text-center py-5">
    <i class="fa-solid fa-calendar-xmark fa-3x text-muted mb-3 d-block"></i>
    <h5 class="text-muted">No appointments yet</h5>
    <a href="/doctors" class="btn btn-teal mt-3">Find a Doctor</a>
  </div>
  {% endif %}
</div>
{% endblock %}""")


LOGIN_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5" style="max-width:440px;">
  <div class="text-center mb-4">
    <i class="fa-solid fa-stethoscope fa-3x mb-3 text-teal d-block"></i>
    <h3 class="fw-bold">Welcome to MediBook</h3>
    <p class="text-muted">Sign in to manage your appointments</p>
  </div>
  <div class="card border-0 shadow-sm rounded-3">
    <div class="card-body p-4">
      <form method="post" action="/login">
        <div class="mb-3">
          <label class="form-label fw-medium">Email Address</label>
          <div class="input-group">
            <span class="input-group-text"><i class="fa-solid fa-envelope"></i></span>
            <input class="form-control" type="email" name="email" placeholder="patient@medibook.com" required>
          </div>
        </div>
        <div class="mb-4">
          <label class="form-label fw-medium">Password</label>
          <div class="input-group">
            <span class="input-group-text"><i class="fa-solid fa-lock"></i></span>
            <input class="form-control" type="password" name="password" placeholder="••••••••" required>
          </div>
        </div>
        <button class="btn btn-teal w-100 py-2 fw-semibold" type="submit">
          <i class="fa-solid fa-right-to-bracket me-2"></i>Sign In
        </button>
      </form>
      <hr class="my-3">
      <div class="rounded p-3" style="background:var(--teal-light); font-size:.88rem;">
        <strong>Demo credentials:</strong><br>
        Patient 1: <code>patient@medibook.com</code> / <code>HealthPass123!</code><br>
        Patient 2: <code>sam@medibook.com</code> / <code>HealthPass123!</code>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    featured = list(DOCTORS.values())[:6]
    return render_template_string(HOME_TMPL, featured=featured)


@app.route("/doctors")
def doctors_list():
    q = request.args.get("q", "").strip().lower()
    specialty = request.args.get("specialty", "").strip()
    docs = list(DOCTORS.values())
    if q:
        docs = [d for d in docs if q in d["name"].lower() or q in d["specialty"].lower()]
    if specialty:
        docs = [d for d in docs if d["specialty"] == specialty]
    specialties = sorted(set(d["specialty"] for d in DOCTORS.values()))
    return render_template_string(DOCTORS_TMPL, doctors=docs, q=q,
                                  specialty=specialty, specialties=specialties)


@app.route("/doctor/<doc_id>")
def doctor_detail(doc_id):
    doc = DOCTORS.get(doc_id)
    if not doc:
        flash("Doctor not found.", "error")
        return redirect(url_for("doctors_list"))
    from datetime import date
    reviews = [
        {"name": "Maria S.", "rating": 5.0, "text": "Absolutely wonderful. Very thorough and explained everything clearly."},
        {"name": "David L.", "rating": 4.8, "text": "Professional and caring. The appointment ran on time."},
        {"name": "Jennifer K.", "rating": 4.9, "text": "One of the best doctors I have ever seen. Highly recommend."},
    ]
    return render_template_string(DOCTOR_DETAIL_TMPL, doc=doc, reviews=reviews,
                                  today=date.today().isoformat())


@app.route("/book", methods=["POST"])
def book():
    if not logged_in():
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    doc_id = request.form.get("doctor_id")
    date_val = request.form.get("date")
    slot = request.form.get("slot")
    reason = request.form.get("reason", "")

    doc = DOCTORS.get(doc_id)
    if not doc:
        flash("Doctor not found.", "error")
        return redirect(url_for("doctors_list"))

    # BUG 1: No slot conflict check — same doctor/date/slot booked by multiple patients
    # Fix would be: check if slot_key exists in a shared booking registry before allowing

    _appt_counter[0] += 1
    appt_id = str(_appt_counter[0])

    appt = {
        "id": appt_id,
        "doctor_id": doc_id,
        "doctor": doc,
        "date": date_val,
        "slot": slot,
        "reason": reason,
        "patient_email": session["email"],
        "status": "Confirmed",
    }
    _appointments[appt_id] = appt

    # Store appt id in session so this patient can see it
    ids = session.get("my_appt_ids", [])
    ids.append(appt_id)
    session["my_appt_ids"] = ids
    session.modified = True

    # BUG 3: redirect to vague success page — no doctor name, date, time, or reference number
    return redirect(url_for("book_success"))


@app.route("/book/success")
def book_success():
    if not logged_in():
        return redirect(url_for("login"))
    return render_template_string(BOOKING_SUCCESS_TMPL)


@app.route("/appointments")
def appointments():
    if not logged_in():
        flash("Please login to view your appointments.", "error")
        return redirect(url_for("login"))
    appt_ids = session.get("my_appt_ids", [])
    appts = [_appointments[aid] for aid in appt_ids if aid in _appointments]
    return render_template_string(APPOINTMENTS_TMPL, appointments=appts)


@app.route("/cancel/<appt_id>")
def cancel(appt_id):
    if not logged_in():
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    appt = _appointments.get(appt_id)
    if not appt:
        flash("Appointment not found.", "error")
        return redirect(url_for("appointments"))

    # BUG 2: IDOR — no ownership check. Any logged-in patient can cancel any
    # appointment by guessing or incrementing the numeric ID in the URL.
    appt["status"] = "Cancelled"

    flash(f"Appointment with {appt['doctor']['name']} has been cancelled.", "success")
    return redirect(url_for("appointments"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = USERS.get(email)
        if user and user["password"] == password:
            session["email"] = email
            session["name"] = user["name"]
            session["my_appt_ids"] = []
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("home"))
        flash("Invalid email or password.", "error")
    return render_template_string(LOGIN_TMPL)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    print(f"MediBook running on http://localhost:{port}")
    print("Login: patient@medibook.com / HealthPass123!")
    print("Planted bugs: double booking, IDOR cancel, vague confirmation")
    app.run(debug=True, port=port)
