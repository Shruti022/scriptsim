# 🚀 ScriptSim: AI-Powered Parallel QA Testing

ScriptSim is a state-of-the-art automated QA testing platform that deploys multiple AI-driven "User Personas" to explore, test, and find bugs in web applications simultaneously. By simulating real-world user behaviors—from confused children to technical power users—ScriptSim provides comprehensive coverage that traditional automated tests often miss.

![Dashboard Preview](https://via.placeholder.com/1200x600/1a1a2e/ffffff?text=ScriptSim+Dashboard+Interface)

## ✨ Key Features

- **🎭 Multi-Persona Testing**: Deploy agents like the "8-Year-Old" (random clicking), "Power User" (technical stress testing), and "Anxious Parent" (privacy/security focus).
- **⚡ Parallel Execution**: Run multiple testing sessions concurrently to slash QA time.
- **🗺️ Automated Site Mapping**: Phase-based approach that first crawls your application to build a comprehensive feature map.
- **📑 Structured Bug Reporting**: Automatically deduplicated, scored, and ranked bug reports powered by Gemini 2.5 Flash.
- **📸 Evidence Capture**: Automated screenshots captured for every discovered issue, stored in Google Cloud Storage.
- **📊 Live Activity Stream**: Real-time logging of agent thoughts, actions, and discoveries as they happen.

## 🏗️ Architecture

```mermaid
graph TD
    User((User)) -->|Configures Scan| Dashboard[Next.js Dashboard]
    Dashboard -->|POST /scan| API[FastAPI Backend]
    API -->|Starts| Orchestrator[Python Orchestrator]
    
    subgraph "AI Core (Google ADK)"
        Orchestrator --> Setup[Setup Agent]
        Setup --> Mapper[Mapper Agent]
        Mapper --> Parallel[Parallel Persona Agents]
        Parallel --> Report[Report Agents]
        Report --> Synthesis[Synthesis & Eval Agent]
    end
    
    Parallel -->|Controls| Browser[Playwright Browser]
    Browser -->|Tests| TargetApp[Target Application]
    
    Parallel -->|Uploads| GCS[Google Cloud Storage]
    Orchestrator -->|Logs| Firestore[Firebase Firestore]
    Dashboard -->|Reads| Firestore
```

## 📂 Project Structure

```text
scriptsim/
├── backend/            # Python Core
│   ├── agents/         # AI Agent definitions (ADK)
│   ├── api/            # FastAPI endpoints
│   ├── schemas/        # Pydantic data models
│   ├── tools/          # Playwright browser tools
│   └── orchestrator.py # Pipeline execution logic
├── frontend/           # Next.js Dashboard
├── apps/               # Target Demo Applications
│   ├── shop/           # E-commerce template (Port 5000)
│   ├── job_board/      # Talent platform (Port 5001)
│   └── doctor_booking/ # Healthcare platform (Port 5002)
├── docs/               # Documentation & Guides
├── scripts/            # Utility & Maintenance scripts
└── start.py            # Unified service orchestrator
```

## 🛠️ Tech Stack

- **Backend**: Python, Google ADK (Agent Development Kit), FastAPI, Playwright
- **AI**: Gemini 2.5 Flash, Vertex AI
- **Database/Storage**: Firebase Firestore, Google Cloud Storage
- **Frontend**: Next.js 14, TailwindCSS (vibrant glassmorphism design)
- **Infrastructure**: Concurrent subprocess management for multi-app deployment

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Cloud Project with Vertex AI enabled
- Firebase project for Firestore

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Shruti022/scriptsim.git
   cd scriptsim
   ```

2. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   SCREENSHOT_BUCKET=your-screenshots-bucket
   ```

3. **Install Dependencies**:
   The `start.py` script handles most installations, but you can manually install if needed:
   ```bash
   pip install -r backend/api/requirements.txt
   cd frontend && npm install && cd ..
   ```

### Running the Platform

Use the unified startup script to launch the dashboard, API, and all demo apps:

```bash
python start.py
```

- **Dashboard**: `http://localhost:3000`
- **Shop App**: `http://localhost:5000`
- **Job Board**: `http://localhost:5001`
- **Doctor Booking**: `http://localhost:5002`

## 🧪 Testing Personas

| Persona | Behavior | Strategy |
| :--- | :--- | :--- |
| **👶 8-Year-Old** | Random, curious | Clicks everything, gets stuck, finds UI dead-ends. |
| **💻 Power User** | Fast, technical | Uses shortcuts, inspects forms, tries to bypass logic. |
| **🛡️ Anxious Parent** | Skeptical, slow | Focuses on privacy links, terms, and safety banners. |
| **👓 Retiree** | Simplified | Looks for high contrast, large buttons, and clear FAQs. |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---
Built with ❤️ for the future of Automated QA.
