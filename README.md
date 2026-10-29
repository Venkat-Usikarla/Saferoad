# 🛣️ SafeRoad — Hyderabad Civic Road Safety Platform

A smart civic reporting and road safety platform empowering citizens of Hyderabad to report road hazards, plan risk-aware travel routes, and mobilize community petitions for urgent municipal repairs.

---

## 🌟 Key Features

1. **Hazard Reporting with Instant Pin-Drop & Reverse Geocoding**
   - Click on Leaflet map to capture GPS coordinates.
   - Real-time GHMC Circle / Municipal Zone auto-detection (6 Hyderabad zones: Charminar, Khairatabad, Secunderabad, Serilingampally, Kukatpally, LB Nagar).
   - Dynamic duplicate detection within 500m.
   - Severity slider with automated priority scoring (Low / Medium / High).
   - Multi-language profanity filter ensuring clean public discourse.

2. **DT Feature 1: SafeRoute (Corridor Safety Navigator)**
   - Enter starting and ending points or pick popular Hyderabad corridors.
   - Interactive OSRM driving polyline generator.
   - Computes a real-time **Route Safety Score (0–100)** and distance-indexed hazard alerts.

3. **DT Feature 2: Community Petitions & Digital Signatures (Change.org-style)**
   - Transform unresolved reports into public civic campaigns.
   - Verified digital signing with locality, phone, and reason.
   - Duplicate signature prevention per email.
   - Instant automated email confirmation to signers.

4. **Multi-tier Municipal Administration**
   - **Chief Municipal Commissioner (Super Admin)**: Complete city-wide jurisdiction.
   - **Regional Circle Administrators (Zonal Admins)**: Scoped access for local circle engineers.

5. **Progressive Web App (PWA)**
   - Installable on mobile phones (Android / iOS) via "Add to Home Screen".
   - Standalone app mode with direct camera and GPS access.

---

## 🚀 Quick Start (Local Setup)

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd PROJECT
   ```

2. **Create virtual environment & install dependencies:**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your Gmail App Password if you wish to enable live email dispatches.

4. **Initialize database & seed sample Hyderabad hazards & petitions:**
   ```bash
   python init_db.py
   ```

5. **Run the server:**
   ```bash
   python app.py
   ```
   Visit `http://127.0.0.1:5000` in your browser.

---

## 🔐 Default Admin Credentials

* **Chief Commissioner (Super Admin):** `admin` / `saferoad2026`
* **Serilingampally Zone (Hitec City / Gachibowli):** `admin_serilingampally` / `serilingampally2026`
* **Khairatabad Zone (Banjara / Jubilee Hills):** `admin_khairatabad` / `khairatabad2026`
* **Secunderabad Zone (Begumpet / Marredpally):** `admin_secunderabad` / `secunderabad2026`
* **Charminar Zone (Old City):** `admin_charminar` / `charminar2026`
* **Kukatpally Zone (Miyapur / KPHB):** `admin_kukatpally` / `kukatpally2026`
* **LB Nagar Zone (Dilsukhnagar):** `admin_lbnagar` / `lbnagar2026`
