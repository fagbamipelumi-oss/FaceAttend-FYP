# FaceAttend-FYP

AI-Based Attendance System Using Face Recognition — Final Year Project.

Supervisor: Mr. Adetolaju.

## Status

Scaffolding stage. Nothing implemented yet.

## Layout

- `backend/` — FastAPI service (enrollment, recognition, attendance, admin API)
- `frontend/` — React (Vite) app: enrollment UI, kiosk capture, admin dashboard, landing page
- `evaluation/` — offline scripts for embedding/verification metrics (Accuracy, Precision, Recall, F1, ROC-AUC, FAR, FRR, EER)
- `data/` — enrollment photos, embeddings, test sets (gitignored — real biometric data, never committed)
- `docs/` — consent forms, design notes
- `report/` — Chapter 1-5 Markdown sources, figures, references, and the docx build script

## Data handling

`data/raw_enrollment/`, `data/embeddings/`, and `data/test_sets/` hold real people's
biometric data and are gitignored. Enrollment requires documented consent first —
see `docs/consent-form.md` once added.
