"""Offline face-verification evaluation.

By default this runs directly against the real enrolled dataset that the
web app has been saving photos into (data/raw_enrollment/<person>/*.jpg,
written automatically on every accepted enrollment photo), so no manual
copying is needed. Optionally point --unknown-dir at a separate folder of
people who were never enrolled, shaped the same way:

    <some folder>/
      <person name>/
        photo1.jpg
        photo2.jpg
        ...

Genuine pairs are built from every pair of photos belonging to the same
enrolled person. Impostor pairs are built from every pair of photos
belonging to two different people (enrolled-vs-enrolled, and, if
--unknown-dir is given, enrolled-vs-unknown).

Usage:
    venv/Scripts/python.exe evaluation/evaluate.py --threshold 0.4
    venv/Scripts/python.exe evaluation/evaluate.py --unknown-dir evaluation/unknown_people --threshold 0.4
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.face_service import (  # noqa: E402
    MultipleFacesFoundError,
    NoFaceFoundError,
    encode_single_face,
    euclidean_distance,
)
from app.services.enrollment_service import load_image_from_bytes  # noqa: E402

from metrics import (  # noqa: E402
    accuracy_precision_recall_f1,
    equal_error_rate,
    far_frr,
    roc_auc,
)


@dataclass
class PersonPhotos:
    name: str
    embeddings: list
    skipped: list[str]


def load_person_embeddings(person_dir: Path) -> PersonPhotos:
    embeddings = []
    skipped = []
    for photo_path in sorted(person_dir.iterdir()):
        if not photo_path.is_file():
            continue
        try:
            image = load_image_from_bytes(photo_path.read_bytes())
            encoding = encode_single_face(image)
            embeddings.append(encoding)
        except NoFaceFoundError:
            skipped.append(f"{photo_path.name}: no face detected")
        except MultipleFacesFoundError as exc:
            skipped.append(f"{photo_path.name}: {exc.count} faces detected")
    return PersonPhotos(name=person_dir.name, embeddings=embeddings, skipped=skipped)


def build_pairs(enrolled_dir: Path, unknown_dir: Path | None) -> tuple[list[float], list[float], dict]:
    if not enrolled_dir.is_dir():
        raise SystemExit(f"Enrolled-photos directory not found: {enrolled_dir}")

    enrolled_people = [load_person_embeddings(p) for p in sorted(enrolled_dir.iterdir()) if p.is_dir()]
    unknown_people = (
        [load_person_embeddings(p) for p in sorted(unknown_dir.iterdir()) if p.is_dir()]
        if unknown_dir and unknown_dir.is_dir()
        else []
    )

    warnings = []
    for person in enrolled_people + unknown_people:
        for reason in person.skipped:
            warnings.append(f"{person.name}/{reason}")
        if len(person.embeddings) == 0:
            warnings.append(f"{person.name}: no usable photos, excluded entirely")

    enrolled_people = [p for p in enrolled_people if p.embeddings]
    unknown_people = [p for p in unknown_people if p.embeddings]

    genuine_distances: list[float] = []
    for person in enrolled_people:
        if len(person.embeddings) < 2:
            warnings.append(f"{person.name}: only 1 usable photo, cannot form a genuine pair")
            continue
        for a, b in combinations(person.embeddings, 2):
            genuine_distances.append(euclidean_distance(a, b))

    impostor_distances: list[float] = []
    for person_a, person_b in combinations(enrolled_people, 2):
        for a in person_a.embeddings:
            for b in person_b.embeddings:
                impostor_distances.append(euclidean_distance(a, b))

    for enrolled_person in enrolled_people:
        for unknown_person in unknown_people:
            for a in enrolled_person.embeddings:
                for b in unknown_person.embeddings:
                    impostor_distances.append(euclidean_distance(a, b))

    stats = {
        "enrolled_people": len(enrolled_people),
        "unknown_people": len(unknown_people),
        "genuine_pairs": len(genuine_distances),
        "impostor_pairs": len(impostor_distances),
        "warnings": warnings,
    }
    return genuine_distances, impostor_distances, stats


DEFAULT_ENROLLED_DIR = Path(__file__).resolve().parents[1] / "data" / "raw_enrollment"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--enrolled-dir",
        type=Path,
        default=DEFAULT_ENROLLED_DIR,
        help=f"Folder of <person>/photo.jpg subfolders. Defaults to the real enrolled dataset at {DEFAULT_ENROLLED_DIR}.",
    )
    parser.add_argument(
        "--unknown-dir",
        type=Path,
        default=None,
        help="Optional folder of <person>/photo.jpg subfolders for people who were never enrolled (impostor-only).",
    )
    parser.add_argument("--threshold", type=float, default=0.4)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()

    genuine, impostor, stats = build_pairs(args.enrolled_dir, args.unknown_dir)

    print(f"Enrolled people: {stats['enrolled_people']}, unknown people: {stats['unknown_people']}")
    print(f"Genuine pairs: {stats['genuine_pairs']}, impostor pairs: {stats['impostor_pairs']}")
    for w in stats["warnings"]:
        print(f"  WARNING: {w}")

    if not genuine or not impostor:
        raise SystemExit(
            "Need at least one genuine pair and one impostor pair to compute metrics. "
            "Add more photos per enrolled person (>=2) and/or more people."
        )

    metrics_at_threshold = accuracy_precision_recall_f1(genuine, impostor, args.threshold)
    far, frr = far_frr(genuine, impostor, args.threshold)
    eer = equal_error_rate(genuine, impostor)
    roc = roc_auc(genuine, impostor)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "enrolled_dir": str(args.enrolled_dir),
        "unknown_dir": str(args.unknown_dir) if args.unknown_dir else None,
        "operating_threshold": args.threshold,
        "dataset_stats": stats,
        "metrics_at_threshold": metrics_at_threshold,
        "far": far,
        "frr": frr,
        "equal_error_rate": eer,
        "roc_auc": roc["auc"],
        "roc_curve": {"fpr": roc["fpr"], "tpr": roc["tpr"], "thresholds": roc["thresholds"]},
        "genuine_distances": genuine,
        "impostor_distances": impostor,
    }

    args.out.mkdir(parents=True, exist_ok=True)
    out_file = args.out / f"evaluation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_file.write_text(json.dumps(report, indent=2))

    print(f"\nAt threshold {args.threshold}:")
    print(f"  Accuracy:  {metrics_at_threshold['accuracy']:.4f}")
    print(f"  Precision: {metrics_at_threshold['precision']:.4f}")
    print(f"  Recall:    {metrics_at_threshold['recall']:.4f}")
    print(f"  F1:        {metrics_at_threshold['f1']:.4f}")
    print(f"  FAR:       {far:.4f}")
    print(f"  FRR:       {frr:.4f}")
    print(f"  EER:       {eer['eer']:.4f} (at threshold {eer['threshold']:.4f})")
    print(f"  ROC-AUC:   {roc['auc']:.4f}")
    print(f"\nFull report written to {out_file}")


if __name__ == "__main__":
    main()
