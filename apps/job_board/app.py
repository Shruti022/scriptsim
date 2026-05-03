"""
TalentHub — Job Board Demo App
Port 5001 | Login: user@talenthub.com / JobPass123!

3 planted bugs:
  1. Applications not persisted — apply succeeds, but My Applications page always empty
     (stores in module-level dict keyed by email, but reads from session['my_apps'])
  2. Sort by salary broken — query param received but ignored, order never changes
  3. Crash on duplicate apply — applying to the same job twice raises KeyError → 500
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import os

app = Flask(__name__)
app.secret_key = "talenthub-demo-secret-2024"

USERS = {
    "user@talenthub.com": {"password": "JobPass123!", "name": "Jordan Lee"},
}

JOBS = [
    {
        "id": "j1",
        "title": "Senior Backend Engineer",
        "company": "Stripe",
        "logo": "S",
        "logo_color": "#635bff",
        "location": "San Francisco, CA",
        "type": "Full-time",
        "salary_min": 180000,
        "salary_max": 240000,
        "tags": ["Python", "Go", "Distributed Systems"],
        "posted": "2 days ago",
        "description": "Join Stripe's payments infrastructure team. You'll build and scale the systems that process hundreds of billions of dollars annually. We work across the full stack from kernel-level networking to high-level API design.",
        "requirements": ["5+ years backend experience", "Strong Python or Go skills", "Experience with distributed systems", "BS/MS in Computer Science or equivalent"],
        "about_company": "Stripe is a financial infrastructure platform for businesses. Millions of companies use Stripe to accept payments, send payouts, and manage their businesses online.",
    },
    {
        "id": "j2",
        "title": "Product Designer",
        "company": "Figma",
        "logo": "F",
        "logo_color": "#1abcfe",
        "location": "New York, NY",
        "type": "Full-time",
        "salary_min": 140000,
        "salary_max": 190000,
        "tags": ["Figma", "Design Systems", "Prototyping"],
        "posted": "1 day ago",
        "description": "Design the future of collaborative design. You'll work on Figma's core product used by over 4 million designers worldwide. This role involves owning end-to-end design for key product areas.",
        "requirements": ["4+ years product design experience", "Strong portfolio showing end-to-end work", "Experience with design systems", "Excellent communication skills"],
        "about_company": "Figma is the leading collaborative design tool. Teams use Figma to design, prototype, and gather feedback — all in one place.",
    },
    {
        "id": "j3",
        "title": "Machine Learning Engineer",
        "company": "Netflix",
        "logo": "N",
        "logo_color": "#e50914",
        "location": "Remote",
        "type": "Full-time",
        "salary_min": 200000,
        "salary_max": 300000,
        "tags": ["PyTorch", "Recommendation Systems", "Python"],
        "posted": "3 days ago",
        "description": "Build ML systems that personalize the Netflix experience for 260M+ subscribers. You'll work on recommendation algorithms, search ranking, and content discovery systems that have direct impact on what the world watches.",
        "requirements": ["MS/PhD in ML, Statistics or related", "3+ years industry ML experience", "PyTorch or TensorFlow proficiency", "Experience with large-scale data pipelines"],
        "about_company": "Netflix is the world's leading streaming entertainment service with 260+ million paid memberships in 190+ countries.",
    },
    {
        "id": "j4",
        "title": "Frontend Engineer",
        "company": "Linear",
        "logo": "L",
        "logo_color": "#5e6ad2",
        "location": "Remote",
        "type": "Full-time",
        "salary_min": 150000,
        "salary_max": 200000,
        "tags": ["React", "TypeScript", "GraphQL"],
        "posted": "5 hours ago",
        "description": "Work on Linear's product used by the best software teams in the world. We care deeply about performance and craft. You'll be responsible for the feel and speed of the entire application.",
        "requirements": ["3+ years React/TypeScript experience", "Strong eye for UI/UX details", "Performance optimization experience", "Familiarity with GraphQL"],
        "about_company": "Linear is the issue tracking tool built for high-performance teams. It streamlines software projects, sprints, tasks, and bug tracking.",
    },
    {
        "id": "j5",
        "title": "DevOps Engineer",
        "company": "HashiCorp",
        "logo": "H",
        "logo_color": "#222222",
        "location": "Austin, TX",
        "type": "Full-time",
        "salary_min": 160000,
        "salary_max": 210000,
        "tags": ["Terraform", "Kubernetes", "AWS"],
        "posted": "1 week ago",
        "description": "HashiCorp's DevOps team manages the infrastructure that powers our cloud products used by Fortune 500 companies. You'll work with Terraform, Vault, and Kubernetes at massive scale.",
        "requirements": ["4+ years DevOps/SRE experience", "Expert Terraform knowledge", "Kubernetes administration", "Strong scripting skills (Bash, Python)"],
        "about_company": "HashiCorp is a leader in infrastructure automation. Their open-source tools — Terraform, Vault, Consul — are used by thousands of enterprises worldwide.",
    },
    {
        "id": "j6",
        "title": "Growth Marketing Manager",
        "company": "Notion",
        "logo": "N",
        "logo_color": "#191919",
        "location": "San Francisco, CA",
        "type": "Full-time",
        "salary_min": 120000,
        "salary_max": 160000,
        "tags": ["Growth", "Analytics", "SEO"],
        "posted": "4 days ago",
        "description": "Drive Notion's next phase of growth. You'll own acquisition channels, run experiments, and work cross-functionally with Product and Engineering to turn data insights into product decisions.",
        "requirements": ["5+ years growth marketing experience", "Strong analytical mindset", "Experience with SQL and analytics tools", "Track record of scaling B2B SaaS growth"],
        "about_company": "Notion is an all-in-one workspace for notes, docs, wikis, and project management. Over 30 million people and teams use Notion.",
    },
    {
        "id": "j7",
        "title": "Part-time Content Writer",
        "company": "Shopify",
        "logo": "S",
        "logo_color": "#96bf48",
        "location": "Remote",
        "type": "Part-time",
        "salary_min": 40000,
        "salary_max": 60000,
        "tags": ["Content Strategy", "SEO", "Copywriting"],
        "posted": "3 days ago",
        "description": "Create compelling product stories and blog content for Shopify's merchant community. You'll write 2-3 articles per week covering e-commerce trends, merchant success stories, and platform updates.",
        "requirements": ["2+ years content writing experience", "Strong SEO knowledge", "E-commerce or SaaS background preferred", "Portfolio of published work"],
        "about_company": "Shopify is a leading e-commerce platform powering over 1.7 million businesses worldwide. We make commerce better for everyone.",
    },
    {
        "id": "j8",
        "title": "Part-time UX Researcher",
        "company": "Airbnb",
        "logo": "A",
        "logo_color": "#ff5a5f",
        "location": "San Francisco, CA",
        "type": "Part-time",
        "salary_min": 50000,
        "salary_max": 75000,
        "tags": ["User Research", "Usability Testing", "Figma"],
        "posted": "6 days ago",
        "description": "Support Airbnb's Host team with qualitative research. You'll run user interviews, usability sessions, and synthesize insights to help improve the hosting experience for millions of hosts globally.",
        "requirements": ["3+ years UX research experience", "Experience with usability testing tools", "Strong synthesis and storytelling skills", "Availability 20 hrs/week"],
        "about_company": "Airbnb is a community marketplace for unique accommodations and experiences around the world. We believe in belonging anywhere.",
    },
    {
        "id": "j9",
        "title": "Contract iOS Developer",
        "company": "Spotify",
        "logo": "S",
        "logo_color": "#1db954",
        "location": "Remote",
        "type": "Contract",
        "salary_min": 100000,
        "salary_max": 150000,
        "tags": ["Swift", "iOS", "Xcode"],
        "posted": "2 days ago",
        "description": "6-month contract to help build Spotify's next-generation iOS features. You'll work embedded with a core product team on the playback and discovery experience used by 600M+ users.",
        "requirements": ["4+ years iOS/Swift experience", "Strong understanding of UIKit and SwiftUI", "Experience with audio APIs a plus", "Available immediately"],
        "about_company": "Spotify is the world's most popular audio streaming platform with over 600 million users and 100 million tracks.",
    },
    {
        "id": "j10",
        "title": "Contract Data Analyst",
        "company": "Uber",
        "logo": "U",
        "logo_color": "#000000",
        "location": "New York, NY",
        "type": "Contract",
        "salary_min": 80000,
        "salary_max": 110000,
        "tags": ["SQL", "Python", "Tableau"],
        "posted": "1 day ago",
        "description": "3-month contract to support Uber's Marketplace Analytics team during a period of rapid expansion. You'll build dashboards, run ad-hoc analyses, and surface pricing insights across markets.",
        "requirements": ["3+ years data analysis experience", "Expert SQL skills", "Python (pandas, numpy)", "Experience with Tableau or Looker"],
        "about_company": "Uber is a technology platform that uses a massive network of people and technology to create new ways to move around the world.",
    },
]

# BUG 1: Applications are stored here (module-level dict keyed by email)
# but My Applications route reads from session['my_apps'] which is never populated
_all_applications: dict = {}  # email -> set of job_ids


def logged_in():
    return "email" in session


# ── Templates ─────────────────────────────────────────────────────────────────

BASE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}TalentHub{% endblock %} — Find Your Dream Job</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
  <style>
    :root { --indigo: #4f46e5; --indigo-dark: #4338ca; --indigo-light: #eef2ff; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f8fafc; }
    .navbar-brand { font-weight: 800; font-size: 1.4rem; color: #fff !important; letter-spacing: -.5px; }
    .navbar-brand span { color: #a5b4fc; }
    .nav-link { color: rgba(255,255,255,.85) !important; }
    .nav-link:hover { color: #fff !important; }
    .hero { background: linear-gradient(135deg, #312e81 0%, #4f46e5 60%, #6366f1 100%); padding: 72px 0 56px; color: #fff; }
    .job-card { border: none; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,.08); transition: transform .2s, box-shadow .2s; background: #fff; }
    .job-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.1); }
    .company-logo { width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem; color: #fff; flex-shrink: 0; }
    .company-logo-lg { width: 72px; height: 72px; font-size: 1.6rem; border-radius: 14px; }
    .tag { background: var(--indigo-light); color: var(--indigo-dark); border-radius: 20px; padding: 3px 12px; font-size: .78rem; font-weight: 600; }
    .type-badge { background: #dcfce7; color: #166534; border-radius: 20px; padding: 3px 10px; font-size: .78rem; font-weight: 600; }
    .remote-badge { background: #fef9c3; color: #854d0e; border-radius: 20px; padding: 3px 10px; font-size: .78rem; font-weight: 600; }
    .btn-indigo { background: var(--indigo); border-color: var(--indigo); color: #fff; }
    .btn-indigo:hover { background: var(--indigo-dark); border-color: var(--indigo-dark); color: #fff; }
    .btn-outline-indigo { border-color: var(--indigo); color: var(--indigo); }
    .btn-outline-indigo:hover { background: var(--indigo); color: #fff; }
    .search-bar { border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,.15); overflow: hidden; }
    .search-bar input, .search-bar select { border: none; padding: 14px 18px; font-size: 1rem; }
    .search-bar input:focus, .search-bar select:focus { box-shadow: none; }
    .search-bar button { border-radius: 0; padding: 14px 28px; }
    .sidebar-card { background: #fff; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,.06); padding: 20px; }
    .text-indigo { color: var(--indigo) !important; }
    footer { background: #0f172a; color: #94a3b8; padding: 48px 0 24px; }
    footer a { color: #94a3b8; text-decoration: none; }
    footer a:hover { color: #fff; }
    .stat-pill { background: rgba(255,255,255,.15); border-radius: 30px; padding: 6px 16px; font-size: .88rem; }
  </style>
</head>
<body>
<nav class="navbar navbar-expand-lg" style="background: var(--indigo-dark);">
  <div class="container">
    <a class="navbar-brand" href="/"><i class="fa-solid fa-briefcase me-2"></i>Talent<span>Hub</span></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="nav">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="/"><i class="fa-solid fa-house me-1"></i>Home</a></li>
        <li class="nav-item"><a class="nav-link" href="/jobs"><i class="fa-solid fa-magnifying-glass me-1"></i>Browse Jobs</a></li>
        {% if session.get('email') %}
        <li class="nav-item"><a class="nav-link" href="/my-applications"><i class="fa-solid fa-file-lines me-1"></i>My Applications</a></li>
        {% endif %}
      </ul>
      <ul class="navbar-nav">
        {% if session.get('email') %}
        <li class="nav-item dropdown">
          <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
            <i class="fa-solid fa-circle-user me-1"></i>{{ session.get('name', 'User') }}
          </a>
          <ul class="dropdown-menu dropdown-menu-end">
            <li><a class="dropdown-item" href="/my-applications"><i class="fa-solid fa-file-lines me-2"></i>My Applications</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item text-danger" href="/logout"><i class="fa-solid fa-right-from-bracket me-2"></i>Logout</a></li>
          </ul>
        </li>
        {% else %}
        <li class="nav-item"><a class="nav-link" href="/login"><i class="fa-solid fa-right-to-bracket me-1"></i>Login</a></li>
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
        <h5 class="text-white mb-3"><i class="fa-solid fa-briefcase me-2"></i>TalentHub</h5>
        <p style="font-size:.9rem;">Connecting exceptional talent with world-class companies. Find your next career move.</p>
      </div>
      <div class="col-md-2">
        <h6 class="text-white mb-3">For Job Seekers</h6>
        <ul class="list-unstyled" style="font-size:.9rem;">
          <li><a href="#">Browse Jobs</a></li>
          <li><a href="#">Career Advice</a></li>
          <li><a href="#">Resume Tips</a></li>
          <li><a href="#">Salary Guide</a></li>
        </ul>
      </div>
      <div class="col-md-2">
        <h6 class="text-white mb-3">For Employers</h6>
        <ul class="list-unstyled" style="font-size:.9rem;">
          <li><a href="#">Post a Job</a></li>
          <li><a href="#">Search Resumes</a></li>
          <li><a href="#">Pricing</a></li>
          <li><a href="#">Enterprise</a></li>
        </ul>
      </div>
      <div class="col-md-2">
        <h6 class="text-white mb-3">Company</h6>
        <ul class="list-unstyled" style="font-size:.9rem;">
          <li><a href="#">About</a></li>
          <li><a href="#">Blog</a></li>
          <li><a href="#">Press</a></li>
          <li><a href="#">Contact</a></li>
        </ul>
      </div>
      <div class="col-md-2">
        <h6 class="text-white mb-3">Follow Us</h6>
        <div class="d-flex gap-3" style="font-size:1.3rem;">
          <a href="#"><i class="fab fa-linkedin"></i></a>
          <a href="#"><i class="fab fa-twitter"></i></a>
          <a href="#"><i class="fab fa-instagram"></i></a>
        </div>
      </div>
    </div>
    <hr style="border-color:#1e293b;">
    <div class="text-center" style="font-size:.85rem;">© 2024 TalentHub Inc. All rights reserved.</div>
  </div>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
{% block scripts %}{% endblock %}
</body>
</html>"""


HOME_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="hero">
  <div class="container text-center">
    <h1 class="fw-bold mb-3" style="font-size:2.8rem;">Find Your Dream Job</h1>
    <p class="mb-4" style="font-size:1.15rem; opacity:.9;">{{ total_jobs }}+ jobs from top companies. Updated daily.</p>
    <form action="/jobs" method="get" class="d-flex search-bar bg-white mx-auto mb-4" style="max-width:680px;">
      <input class="form-control flex-grow-1" type="text" name="q" placeholder="Job title, company, or keyword..." value="">
      <select class="form-select" name="type" style="max-width:160px; border-left:1px solid #e2e8f0;">
        <option value="">All Types</option>
        <option>Full-time</option>
        <option>Part-time</option>
        <option>Contract</option>
        <option>Remote</option>
      </select>
      <button class="btn btn-indigo px-4" type="submit"><i class="fa-solid fa-magnifying-glass me-2"></i>Search</button>
    </form>
    <div class="d-flex justify-content-center gap-3 flex-wrap">
      <span class="stat-pill"><i class="fa-solid fa-building me-1"></i>500+ Companies</span>
      <span class="stat-pill"><i class="fa-solid fa-user-tie me-1"></i>{{ total_jobs }}+ Open Roles</span>
      <span class="stat-pill"><i class="fa-solid fa-handshake me-1"></i>50K+ Hires Made</span>
    </div>
  </div>
</div>

<div class="container py-5">
  <div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold mb-0">Featured Opportunities</h2>
    <a href="/jobs" class="btn btn-outline-indigo btn-sm">Browse All <i class="fa-solid fa-arrow-right ms-1"></i></a>
  </div>
  <div class="row g-4">
    {% for job in featured %}
    <div class="col-md-6">
      <div class="job-card p-4">
        <div class="d-flex align-items-start gap-3 mb-3">
          <div class="company-logo" style="background:{{ job.logo_color }}">{{ job.logo }}</div>
          <div class="flex-grow-1">
            <h6 class="fw-semibold mb-0">{{ job.title }}</h6>
            <div class="text-muted" style="font-size:.88rem;">{{ job.company }}</div>
          </div>
          <div class="text-muted" style="font-size:.8rem;">{{ job.posted }}</div>
        </div>
        <div class="d-flex gap-2 flex-wrap mb-3">
          <span class="type-badge">{{ job.type }}</span>
          {% if 'Remote' in job.location %}
          <span class="remote-badge"><i class="fa-solid fa-wifi me-1"></i>Remote</span>
          {% else %}
          <span class="text-muted" style="font-size:.83rem;"><i class="fa-solid fa-location-dot me-1"></i>{{ job.location }}</span>
          {% endif %}
        </div>
        <div class="d-flex gap-1 flex-wrap mb-3">
          {% for tag in job.tags[:3] %}
          <span class="tag">{{ tag }}</span>
          {% endfor %}
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <span class="fw-semibold text-indigo">${{ '{:,}'.format(job.salary_min) }} – ${{ '{:,}'.format(job.salary_max) }}</span>
          <a href="/job/{{ job.id }}" class="btn btn-indigo btn-sm px-3">View Job</a>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
</div>

<div class="py-5" style="background: var(--indigo-light);">
  <div class="container text-center">
    <h2 class="fw-bold mb-5">Why TalentHub?</h2>
    <div class="row g-4">
      <div class="col-md-4">
        <i class="fa-solid fa-bolt fa-2x text-indigo mb-3 d-block"></i>
        <h5 class="fw-semibold">Apply in Minutes</h5>
        <p class="text-muted">One-click apply with your saved profile. No more filling out the same form repeatedly.</p>
      </div>
      <div class="col-md-4">
        <i class="fa-solid fa-shield-halved fa-2x text-indigo mb-3 d-block"></i>
        <h5 class="fw-semibold">Verified Companies</h5>
        <p class="text-muted">Every company is vetted. No fake listings, no spam, just real opportunities.</p>
      </div>
      <div class="col-md-4">
        <i class="fa-solid fa-chart-line fa-2x text-indigo mb-3 d-block"></i>
        <h5 class="fw-semibold">Salary Transparency</h5>
        <p class="text-muted">Every listing shows salary ranges. Know what you're worth before you apply.</p>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")


JOBS_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5">
  <div class="row g-4">
    <div class="col-lg-3">
      <form action="/jobs" method="get">
        <div class="sidebar-card mb-3">
          <h6 class="fw-semibold mb-3">Search</h6>
          <input class="form-control" type="text" name="q" placeholder="Keywords..." value="{{ q }}">
        </div>
        <div class="sidebar-card mb-3">
          <h6 class="fw-semibold mb-3">Job Type</h6>
          {% for t in ['Full-time', 'Part-time', 'Contract', 'Remote'] %}
          <div class="form-check mb-1">
            <input class="form-check-input" type="checkbox" name="type" value="{{ t }}" id="type_{{ loop.index }}"
              {% if t in selected_types %}checked{% endif %}>
            <label class="form-check-label" for="type_{{ loop.index }}">{{ t }}</label>
          </div>
          {% endfor %}
        </div>
        <div class="sidebar-card mb-3">
          <h6 class="fw-semibold mb-3">Sort By</h6>
          <!-- BUG 2: sort param is sent correctly but server ignores it entirely -->
          <select class="form-select" name="sort">
            <option value="recent" {% if sort == 'recent' %}selected{% endif %}>Most Recent</option>
            <option value="salary_high" {% if sort == 'salary_high' %}selected{% endif %}>Salary: High to Low</option>
            <option value="salary_low" {% if sort == 'salary_low' %}selected{% endif %}>Salary: Low to High</option>
          </select>
        </div>
        <button class="btn btn-indigo w-100" type="submit"><i class="fa-solid fa-filter me-2"></i>Apply Filters</button>
        <a href="/jobs" class="btn btn-outline-secondary w-100 mt-2">Clear All</a>
      </form>
    </div>

    <div class="col-lg-9">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="fw-semibold mb-0">{{ jobs|length }} jobs found</h5>
        {% if q %}<span class="text-muted">Results for "<strong>{{ q }}</strong>"</span>{% endif %}
      </div>
      <div class="d-flex flex-column gap-3">
        {% for job in jobs %}
        <div class="job-card p-4">
          <div class="d-flex align-items-start gap-3">
            <div class="company-logo" style="background:{{ job.logo_color }}">{{ job.logo }}</div>
            <div class="flex-grow-1">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <h6 class="fw-semibold mb-0">{{ job.title }}</h6>
                  <div class="text-muted" style="font-size:.88rem;">{{ job.company }}</div>
                </div>
                <span class="text-muted" style="font-size:.8rem;">{{ job.posted }}</span>
              </div>
              <div class="d-flex gap-2 flex-wrap my-2">
                <span class="type-badge">{{ job.type }}</span>
                <span class="text-muted" style="font-size:.83rem;"><i class="fa-solid fa-location-dot me-1"></i>{{ job.location }}</span>
              </div>
              <div class="d-flex gap-1 flex-wrap mb-2">
                {% for tag in job.tags %}
                <span class="tag">{{ tag }}</span>
                {% endfor %}
              </div>
              <div class="d-flex justify-content-between align-items-center mt-2">
                <span class="fw-semibold text-indigo">${{ '{:,}'.format(job.salary_min) }} – ${{ '{:,}'.format(job.salary_max) }}/yr</span>
                <a href="/job/{{ job.id }}" class="btn btn-indigo btn-sm px-3">View &amp; Apply</a>
              </div>
            </div>
          </div>
        </div>
        {% endfor %}
        {% if not jobs %}
        <div class="text-center py-5">
          <i class="fa-solid fa-briefcase fa-3x text-muted mb-3 d-block"></i>
          <h5 class="text-muted">No jobs match your filters</h5>
          <a href="/jobs" class="btn btn-outline-indigo mt-2">Clear Filters</a>
        </div>
        {% endif %}
      </div>
    </div>
  </div>
</div>
{% endblock %}""")


JOB_DETAIL_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5">
  <nav aria-label="breadcrumb" class="mb-4">
    <ol class="breadcrumb">
      <li class="breadcrumb-item"><a href="/" class="text-indigo">Home</a></li>
      <li class="breadcrumb-item"><a href="/jobs" class="text-indigo">Jobs</a></li>
      <li class="breadcrumb-item active">{{ job.title }}</li>
    </ol>
  </nav>
  <div class="row g-4">
    <div class="col-lg-8">
      <div class="job-card p-4 mb-4">
        <div class="d-flex align-items-start gap-4 mb-4">
          <div class="company-logo company-logo-lg" style="background:{{ job.logo_color }}">{{ job.logo }}</div>
          <div>
            <h3 class="fw-bold mb-1">{{ job.title }}</h3>
            <h5 class="text-muted fw-normal mb-2">{{ job.company }}</h5>
            <div class="d-flex gap-2 flex-wrap">
              <span class="type-badge fs-6">{{ job.type }}</span>
              <span class="text-muted"><i class="fa-solid fa-location-dot me-1"></i>{{ job.location }}</span>
              <span class="text-muted"><i class="fa-solid fa-clock me-1"></i>{{ job.posted }}</span>
            </div>
          </div>
        </div>
        <div class="d-flex gap-1 flex-wrap mb-3">
          {% for tag in job.tags %}
          <span class="tag">{{ tag }}</span>
          {% endfor %}
        </div>
        <div class="p-3 rounded-3" style="background:var(--indigo-light);">
          <span class="fw-bold text-indigo fs-5">${{ '{:,}'.format(job.salary_min) }} – ${{ '{:,}'.format(job.salary_max) }} / year</span>
        </div>
      </div>

      <div class="job-card p-4 mb-4">
        <h5 class="fw-semibold mb-3">About the Role</h5>
        <p class="text-muted">{{ job.description }}</p>
      </div>

      <div class="job-card p-4 mb-4">
        <h5 class="fw-semibold mb-3">Requirements</h5>
        <ul class="text-muted ps-3">
          {% for req in job.requirements %}
          <li class="mb-1">{{ req }}</li>
          {% endfor %}
        </ul>
      </div>

      <div class="job-card p-4">
        <h5 class="fw-semibold mb-3">About {{ job.company }}</h5>
        <p class="text-muted">{{ job.about_company }}</p>
      </div>
    </div>

    <div class="col-lg-4">
      <div class="job-card p-4 sticky-top" style="top:80px;">
        <h5 class="fw-semibold mb-3">Apply for this Job</h5>
        {% if session.get('email') %}
        <form action="/apply/{{ job.id }}" method="post" enctype="multipart/form-data">
          <div class="mb-3">
            <label class="form-label fw-medium">Full Name</label>
            <input class="form-control" type="text" name="name" value="{{ session.get('name', '') }}" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-medium">Email</label>
            <input class="form-control" type="email" name="email" value="{{ session.get('email', '') }}" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-medium">Phone</label>
            <input class="form-control" type="tel" name="phone" placeholder="+1 (555) 000-0000">
          </div>
          <div class="mb-3">
            <label class="form-label fw-medium">Resume (PDF)</label>
            <input class="form-control" type="file" name="resume" accept=".pdf,.doc,.docx">
          </div>
          <div class="mb-3">
            <label class="form-label fw-medium">Cover Letter</label>
            <textarea class="form-control" name="cover_letter" rows="3" placeholder="Why are you a great fit?"></textarea>
          </div>
          <button class="btn btn-indigo w-100 py-2 fw-semibold" type="submit">
            <i class="fa-solid fa-paper-plane me-2"></i>Submit Application
          </button>
        </form>
        {% else %}
        <div class="text-center py-3">
          <i class="fa-solid fa-lock fa-2x text-muted mb-3 d-block"></i>
          <p class="text-muted mb-3">Login to apply for this position</p>
          <a href="/login" class="btn btn-indigo w-100">Login to Apply</a>
        </div>
        {% endif %}
      </div>
    </div>
  </div>
</div>
{% endblock %}""")


APPLY_SUCCESS_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5" style="max-width:560px;">
  <div class="job-card p-5 text-center">
    <i class="fa-solid fa-circle-check fa-3x text-indigo mb-4 d-block"></i>
    <h3 class="fw-bold mb-2">Application Submitted!</h3>
    <p class="text-muted mb-4">
      Your application has been received. The {{ company }} team will review it and get back to you soon.
    </p>
    <div class="p-3 rounded-3 text-start mb-4" style="background:var(--indigo-light); font-size:.9rem;">
      <div><strong>Position:</strong> {{ job_title }}</div>
      <div><strong>Company:</strong> {{ company }}</div>
      <div class="text-muted mt-1">You'll receive a confirmation at {{ session.get('email') }}</div>
    </div>
    <div class="d-flex gap-3 justify-content-center">
      <a href="/my-applications" class="btn btn-indigo px-4">My Applications</a>
      <a href="/jobs" class="btn btn-outline-secondary px-4">Browse More Jobs</a>
    </div>
  </div>
</div>
{% endblock %}""")


MY_APPLICATIONS_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5">
  <h2 class="fw-bold mb-4">My Applications</h2>
  {% if applications %}
  <div class="d-flex flex-column gap-3">
    {% for job in applications %}
    <div class="job-card p-4">
      <div class="d-flex align-items-center gap-3">
        <div class="company-logo" style="background:{{ job.logo_color }}">{{ job.logo }}</div>
        <div class="flex-grow-1">
          <h6 class="fw-semibold mb-0">{{ job.title }}</h6>
          <div class="text-muted" style="font-size:.88rem;">{{ job.company }}</div>
        </div>
        <span class="badge bg-warning text-dark">Under Review</span>
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <div class="text-center py-5">
    <i class="fa-solid fa-file-circle-xmark fa-3x text-muted mb-3 d-block"></i>
    <h5 class="text-muted">No applications yet</h5>
    <p class="text-muted">Start applying to jobs to track your progress here.</p>
    <a href="/jobs" class="btn btn-indigo mt-2">Browse Jobs</a>
  </div>
  {% endif %}
</div>
{% endblock %}""")


LOGIN_TMPL = BASE.replace("{% block content %}{% endblock %}", """{% block content %}
<div class="container py-5" style="max-width:440px;">
  <div class="text-center mb-4">
    <i class="fa-solid fa-briefcase fa-3x text-indigo mb-3 d-block"></i>
    <h3 class="fw-bold">Welcome Back</h3>
    <p class="text-muted">Sign in to manage your job applications</p>
  </div>
  <div class="job-card p-4">
    <form method="post" action="/login">
      <div class="mb-3">
        <label class="form-label fw-medium">Email Address</label>
        <div class="input-group">
          <span class="input-group-text"><i class="fa-solid fa-envelope"></i></span>
          <input class="form-control" type="email" name="email" placeholder="user@talenthub.com" required>
        </div>
      </div>
      <div class="mb-4">
        <label class="form-label fw-medium">Password</label>
        <div class="input-group">
          <span class="input-group-text"><i class="fa-solid fa-lock"></i></span>
          <input class="form-control" type="password" name="password" placeholder="••••••••" required>
        </div>
      </div>
      <button class="btn btn-indigo w-100 py-2 fw-semibold" type="submit">
        <i class="fa-solid fa-right-to-bracket me-2"></i>Sign In
      </button>
    </form>
    <hr class="my-3">
    <div class="rounded p-3" style="background:var(--indigo-light); font-size:.88rem;">
      <strong>Demo credentials:</strong><br>
      Email: <code>user@talenthub.com</code><br>
      Password: <code>JobPass123!</code>
    </div>
  </div>
</div>
{% endblock %}""")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template_string(HOME_TMPL, featured=JOBS[:4], total_jobs=len(JOBS))


@app.route("/jobs")
def jobs():
    q = request.args.get("q", "").strip().lower()
    selected_types = request.args.getlist("type")
    sort = request.args.get("sort", "recent")  # BUG 2: received but never used

    results = list(JOBS)

    if q:
        results = [j for j in results if q in j["title"].lower() or q in j["company"].lower()
                   or any(q in t.lower() for t in j["tags"])]

    if selected_types:
        results = [j for j in results if j["type"] in selected_types
                   or ("Remote" in selected_types and "Remote" in j["location"])]

    # BUG 2: sort is completely ignored — always stays in default insertion order
    # Fix would be: if sort == 'salary_high': results.sort(key=lambda j: j['salary_max'], reverse=True)

    return render_template_string(JOBS_TMPL, jobs=results, q=q,
                                  selected_types=selected_types, sort=sort)


@app.route("/job/<job_id>")
def job_detail(job_id):
    job = next((j for j in JOBS if j["id"] == job_id), None)
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("jobs"))
    return render_template_string(JOB_DETAIL_TMPL, job=job)


@app.route("/apply/<job_id>", methods=["POST"])
def apply(job_id):
    if not logged_in():
        flash("Please login to apply.", "error")
        return redirect(url_for("login"))

    job = next((j for j in JOBS if j["id"] == job_id), None)
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("jobs"))

    email = session["email"]

    if email not in _all_applications:
        _all_applications[email] = set()

    # BUG 3: Duplicate apply crashes with 500 instead of showing "Already Applied"
    if job_id in _all_applications[email]:
        raise RuntimeError(f"apply_service: duplicate entry detected for job={job_id}")

    _all_applications[email].add(job_id)

    # BUG 1: saved to _all_applications, but My Applications reads session['my_apps']
    # session['my_apps'] is never set, so the page always shows empty

    return render_template_string(APPLY_SUCCESS_TMPL,
                                  job_title=job["title"], company=job["company"])


@app.route("/my-applications")
def my_applications():
    if not logged_in():
        flash("Please login to view your applications.", "error")
        return redirect(url_for("login"))

    # BUG 1: reads session['my_apps'] which is never populated — always empty list
    applied_ids = session.get("my_apps", [])
    applications = [j for j in JOBS if j["id"] in applied_ids]

    return render_template_string(MY_APPLICATIONS_TMPL, applications=applications)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = USERS.get(email)
        if user and user["password"] == password:
            session["email"] = email
            session["name"] = user["name"]
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
    port = int(os.environ.get("PORT", 5001))
    print(f"TalentHub running on http://localhost:{port}")
    print("Login: user@talenthub.com / JobPass123!")
    print("Planted bugs: applications not persisted, sort ignored, crash on duplicate apply")
    app.run(debug=True, port=port)
