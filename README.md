# CodeDNA – Git Behaviour Analysis and AI-Based Developer Productivity and Burnout-Risk Prediction

A master's degree project (MCA, 3rd Semester, Vidyavardhaka College of Engineering) that analyses GitHub repository activity to understand developer behaviour patterns, estimate productivity trends, surface possible burnout-related warning indicators, and classify code samples as human-written or AI-generated.

**Student:** Rejoy Immanuel D (USN: 4VV25MC074)
**Guide:** Yashwanth Kumar

---

## Project Overview

CodeDNA collects GitHub activity via the GitHub REST API and applies machine-learning and NLP techniques to:

1. **Behaviour & Anomaly Analysis** – Isolation Forest detects activity patterns deviating from a developer's historical baseline.
2. **Commit-Message Analysis** – NLTK-based NLP explores changes in message patterns (descriptive only).
3. **Productivity Trend Estimation** – Repository-based indicators over time (not a complete productivity measure).
4. **AI-Code Classification** – Supervised classifier (TF-IDF + code features) estimates human-written vs AI-generated code.
5. **Interactive Dashboard** – Angular + Chart.js frontend visualising timelines, heatmaps, anomaly alerts, and classification results.

**Important:** The system presents possible burnout-related indicators, **not a medical diagnosis**. AI-code predictions are estimates, not proof of authorship.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask, Flask-CORS |
| Data Collection | GitHub REST API v3 |
| ML / Anomaly | scikit-learn (Isolation Forest, RandomForest) |
| NLP | NLTK |
| Frontend | Angular 17, Bootstrap 5, Chart.js |
| Database | SQLite (SQLAlchemy ORM) |

---

## Directory Structure

```
CodeDNA/
├── backend/
│   ├── app.py                 # Flask application entry point
│   ├── database.py            # SQLAlchemy models & DB init
│   ├── data_collection.py     # GitHub REST API client
│   ├── preprocessing.py       # Data cleaning & aggregation
│   ├── features.py            # Behavioural feature extraction
│   ├── anomaly_detection.py   # Isolation Forest anomaly detector
│   ├── nlp_analysis.py        # Commit-message NLP analysis
│   ├── productivity.py        # Productivity trend estimation
│   ├── code_classifier.py     # AI vs human code classifier
│   ├── generate_sample_data.py# Script to create sample training data
│   ├── requirements.txt       # Python dependencies
│   └── codedna.db             # SQLite database (created on first run)
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── app.component.ts
│   │   │   ├── app.routes.ts
│   │   │   ├── services/api.service.ts
│   │   │   ├── components/
│   │   │   │   ├── navbar/
│   │   │   │   ├── dashboard/
│   │   │   │   ├── repo-collection/
│   │   │   │   └── code-classification/
│   │   │   └── app.config.ts
│   │   ├── index.html
│   │   ├── styles.css
│   │   ├── main.ts
│   │   └── polyfills.ts
│   ├── angular.json
│   ├── package.json
│   ├── tsconfig.json
│   └── tsconfig.app.json
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm (for Angular frontend)
- GitHub personal access token (optional, but recommended to avoid API rate limits)

### Backend Setup

```bash
cd CodeDNA/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# or: source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# (Optional) Set GitHub token for higher rate limits
set GITHUB_TOKEN=your_github_token   # Windows
# or: export GITHUB_TOKEN=your_github_token   # Linux/Mac

# Run the backend
python app.py
```

The Flask backend will start at `http://localhost:5000`.

### Frontend Setup

```bash
cd CodeDNA/frontend

# Install dependencies
npm install

# Start the development server
ng serve
```

The Angular app will start at `http://localhost:4200` and proxy API calls to the Flask backend at `http://localhost:5000`.

**Note:** The frontend calls `http://localhost:5000/api/...` directly. Make sure the backend is running before using the frontend.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/repositories/collect` | Collect repo data from GitHub API |
| GET | `/api/repositories` | List tracked repositories |
| GET | `/api/repositories/{id}/features` | Behavioural features |
| GET | `/api/repositories/{id}/anomalies` | Anomaly detection results |
| GET | `/api/repositories/{id}/nlp` | Commit-message NLP analysis |
| GET | `/api/repositories/{id}/productivity` | Productivity indicators |
| GET | `/api/dashboard/{id}` | Combined dashboard data |
| POST | `/api/classify/train` | Train AI-code classifier |
| POST | `/api/classify/predict` | Classify a code sample |

---

## Using the Application

### 1. Collect Repository Data

Navigate to **Collect Repository**, enter a GitHub owner and repository name (e.g., owner: `facebook`, repo: `react`), and click **Collect Data**. The system fetches commit history via the GitHub API and stores it in the local SQLite database.

### 2. View Dashboard

Navigate to **Dashboard**, select a repository from the dropdown, and view:
- Commit timeline (line chart)
- Time-of-day distribution (bar chart)
- Productivity indicators (commits/day, active days, consistency)
- Behavioural features

### 3. AI Code Classification

Navigate to **AI Code Classification**:
- Optionally train the classifier with labelled samples (1 = AI-generated, 0 = human-written)
- Enter a code snippet and click **Classify** to get an estimate with confidence score

---

## Generating Sample Training Data

The backend includes a script to generate sample human-written and AI-generated code samples for testing the classifier:

```bash
cd backend
python generate_sample_data.py
```

This creates a `sample_training_data.json` file with balanced examples that you can use to train the classifier via the `/api/classify/train` endpoint.

---

## Limitations (Documented per Project Synopsis)

- **GitHub API rate limits:** Unauthenticated requests are limited to 60/hour. Use a personal access token for higher limits.
- **Burnout indicators:** Repository activity alone cannot establish psychological burnout. These are reflection indicators, not medical diagnoses.
- **AI-code detection:** Classifiers may misclassify human-AI co-authored code and may not generalise across languages or models. Predictions are probabilistic estimates.
- **Productivity:** Commit-based indicators are not a complete measure of individual developer productivity.

---

## References

1. Tulili, T. R., Capiluppi, A., & Rastogi, A. (2023). Burnout in Software Engineering: A Systematic Mapping Study. *Information and Software Technology*, 155, 107116.
2. Zhang et al. (2024). Understanding Work Rhythms in Software Development and Their Effects on Technical Performance. *IET Software*.
3. GPTSniffer: A CodeBERT-Based Classifier to Detect Source Code Written by ChatGPT (2024). *Journal of Systems and Software*, 214, 112059.
4. Demirok, B., & Kutlu, M. (2025). AIGCodeSet: A New Annotated Dataset for AI Generated Code Detection. *SIU 2025*.
5. Orel, D., et al. (2025). Droid: A Resource Suite for AI-Generated Code Detection. *EMNLP 2025*.
6. Boukili, G., et al. (2026). A Dataset for Human-Written and AI-Generated Code Source Classification. *Data in Brief*, 65, 112527.
>>>>>>> 05c4903 (Initial commit: CodeDNA - Git behaviour analysis, developer productivity & burnout-risk prediction, AI-vs-human code classification)
