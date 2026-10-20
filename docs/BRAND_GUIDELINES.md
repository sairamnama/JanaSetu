# BRAND & DESIGN SYSTEM GUIDELINES: GRAMSEVA (గ్రామసేవ)
**Project:** Rural Panchayat Web-Based Grievance Management System  
**Organization:** Community Service Project (CSP) — e-Panchayat Governance  
**Version:** 1.0  
**Effective Date:** October 2026  

---

## 1. Brand Identity & Purpose

### 1.1 Brand Name
- **Primary:** **GramSeva**
- **Bilingual Title:** **GramSeva | గ్రామసేవ (Panchayat Grievance Portal)**
- **Tagline:** *Empowering Rural Citizens, Ensuring Transparent Panchayat Governance.*

### 1.2 Brand Character & Voice
- **Trustworthy & Authoritative:** Instills confidence that complaints are officially recorded and monitored by the Sarpanch and Panchayat Secretary.
- **Dignified & Citizen-Centric:** Treats every villager’s issue—from water leakage to streetlights—with dignity and prompt attention.
- **Clear & Uncluttered:** Eliminates bureaucratic jargon in favor of self-explanatory icons, readable status cards, and visual timelines.

---

## 2. Color Palette & Design Tokens

GramSeva combines the grounding dignity of Indian civic green with modern digital government aesthetics and high-contrast accessibility.

```css
:root {
  /* Brand Civic Tones */
  --civic-dark: #0A3622;          /* Deepest Government Forest */
  --civic-primary: #0F5132;       /* Primary Panchayat Green */
  --civic-primary-hover: #084026; /* Hover Accent */
  --civic-accent: #198754;        /* Vibrant Field Green */
  --civic-subtle: #E8F5E9;        /* Soft Tint Background */
  --civic-border: #C8E6C9;        /* Soft Border Accent */

  /* Saffron & Solar Accents */
  --saffron-primary: #EA580C;     /* Civic Saffron */
  --saffron-light: #FFEDD5;       /* Warm Glow */
  --panchayat-gold: #F59E0B;      /* Panchayat Emblem Gold */

  /* Neutral Surface Palette */
  --bg-page: #F8FAFC;             /* Ultra-clean Slate Page Background */
  --bg-surface: #FFFFFF;          /* Pure White Card Surface */
  --bg-surface-alt: #F1F5F9;      /* Alt Tint Surface */
  --border-subtle: #E2E8F0;       /* Card and Table Borders */
  --border-focus: #10B981;        /* Focus State Ring */

  /* Typography Colors */
  --text-main: #0F172A;           /* Deep Charcoal / Near Black */
  --text-muted: #475569;          /* Secondary Grey */
  --text-subtle: #94A3B8;         /* Tertiary / Placeholders */
  --text-inverse: #FFFFFF;        /* Text on Dark Buttons */

  /* Status Colors (Standardized) */
  --status-submitted: #0284C7;    /* Sky Blue */
  --status-submitted-bg: #E0F2FE;
  --status-review: #6366F1;       /* Indigo */
  --status-review-bg: #EEF2FF;
  --status-assigned: #8B5CF6;     /* Royal Purple */
  --status-assigned-bg: #F3E8FF;
  --status-progress: #D97706;     /* Warm Amber */
  --status-progress-bg: #FEF3C7;
  --status-resolved: #15803D;     /* Emerald Resolved */
  --status-resolved-bg: #DCFCE7;
  --status-closed: #475569;       /* Charcoal Slate */
  --status-closed-bg: #F1F5F9;
  --status-rejected: #DC2626;     /* Alert Crimson */
  --status-rejected-bg: #FEE2E2;

  /* Priority Tokens */
  --priority-high: #DC2626;
  --priority-high-bg: #FEF2F2;
  --priority-medium: #D97706;
  --priority-medium-bg: #FFFBEB;
  --priority-low: #2563EB;
  --priority-low-bg: #EFF6FF;

  /* Elevation & Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
  --shadow-glow: 0 0 20px rgba(16, 185, 129, 0.25);

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-full: 9999px;
}
```

---

## 3. Typography & Hierarchy

### 3.1 Web Font Selection
- **Primary Display & Headings:** `Plus Jakarta Sans`, system-ui, sans-serif  
  *Characteristics: Modern, legible, confident geometric proportions.*
- **Body & Data Displays:** `Inter`, -apple-system, sans-serif  
  *Characteristics: Neutral, high x-height, optimal clarity on mobile screens.*
- **Indic Script Support (Bilingual):** `Noto Sans Telugu`, `Noto Sans Devanagari`

### 3.2 Scale & Weights
- **H1 / Portal Header:** 28px – 32px (Bold 700, Line Height 1.25)
- **H2 / Section Title:** 20px – 24px (SemiBold 600, Line Height 1.3)
- **H3 / Card Title:** 16px – 18px (SemiBold 600)
- **Body Regular:** 14px – 15px (Regular 400, Line Height 1.5)
- **Caption / Metadata:** 12px – 13px (Medium 500)
- **Badges / Pill Tags:** 11px – 12px (SemiBold 600, All Caps tracking +0.03em)

---

## 4. UI Components & Layout Principles

### 4.1 Header & Civic Bar
- Features the national/civic crest emblem, Panchayat name (e.g. *Ananthapur Gram Panchayat*), and live time.
- Right navigation features quick language toggle (`EN | తెలుగు`), role switcher for demonstration, and notification counter pill.

### 4.2 Status Timeline Component
- Interactive horizontal/vertical stepper showing the 6 stages:
  1. Submitted (నమోదైంది)
  2. Under Review (పరిశీలనలో ఉంది)
  3. Assigned (అధికారికి కేటాయించబడింది)
  4. In Progress (పని జరుగుతోంది)
  5. Resolved (పరిష్కరించబడింది)
  6. Closed (ముగిసింది)
- Active steps pulse with a glowing emerald or amber halo.

### 4.3 Grievance Cards & Data Tables
- Hover elevation transition (`transform: translateY(-2px); box-shadow: var(--shadow-md)`).
- Distinct color-coded category chips (Water 💧, Power ⚡, Sanitation 🧹, Roads 🛣️, Health 🏥, School 🏫).
- Action buttons have minimum 44px height for touch accessibility.

### 4.4 Citizen Feedback Module
- 5-Star interactive rating component with golden hover animations.
- Quick satisfaction buttons: **Fully Satisfied**, **Partially Satisfied**, **Unsatisfied**.

### 4.5 Official Analytics Visualizations
- Implemented with Chart.js adhering to brand palette:
  - Category breakdown: Doughnut chart with harmonious civic green, sky, amber, indigo, and teal slices.
  - Ward resolution speed: Bar chart comparing pending vs resolved.
  - 6-Month intake trend: Smooth curved spline line chart with area gradient fill.

---

## 5. Micro-Animations & Responsiveness

1. **Card Hover Effect:** 0.2s ease-in-out subtle vertical lift and border glow.
2. **Badge Pulse:** Urgent/High priority badges feature an animated soft red beacon dot.
3. **Toast Notifications:** Slide down from top-right with auto-dismiss after 4 seconds.
4. **Mobile First:** Optimized for screens down to 320px width; tabs convert into horizontal scroll chips or bottom navigation on small screens.
