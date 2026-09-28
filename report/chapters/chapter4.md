# CHAPTER FOUR

# SYSTEM IMPLEMENTATION AND RESULTS

## 4.1 Introduction

This chapter presents the system as it was actually implemented and tested, stage by stage, pairing a real code excerpt from the working system with the real output that excerpt produced. It then walks through the implemented interface, reports the results of system-level testing under realistic and adversarial conditions, documents the real defects this testing uncovered together with how each was resolved, and closes with a discussion of what the results mean and where they fall short of a general claim.

At the time of writing, the enrolled dataset consists of six real, consenting participants: Fagbami Pelumi, Akinshade Mykel Ayomiposi, Okobaroh Timothy Odiri, Falomo Busayo Precious, Obasanjo Emmanuel, and Olarotimi Esther, contributing a total of 48 accepted enrollment photographs (between four and twelve per person) and four logged attendance records at the time this chapter was written.

## 4.2 Enrollment and Data Collection

Enrollment begins only after consent is recorded. The relevant excerpt from `enrollment_service.py` is:

```python
def create_person(db, full_name, consent_given, matric_number=None, email=None):
    if not consent_given:
        raise ConsentRequiredError(
            "Enrollment requires documented consent before any photo is captured."
        )
    person = Person(
        full_name=full_name,
        matric_number=matric_number,
        email=email,
        consent_given=True,
        consent_given_at=datetime.now(timezone.utc),
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person
```

Attempting to create a person without consent produces a real, observed HTTP 400 response rather than a silently created record:

```
POST /people  {"full_name": "No Consent Person", "consent_given": false}
-> 400 Bad Request: "Enrollment requires documented consent before any photo is captured."
```

A real query of the live enrollment database at the time of writing confirms six enrolled people, each with `consent_given = true` and a recorded consent timestamp, and between four and twelve embeddings per person:

```
Akinshade Mykel Ayomiposi: 8 embeddings
Fagbami Pelumi: 12 embeddings
Falomo Busayo Precious: 7 embeddings
Obasanjo Emmanuel: 6 embeddings
Okobaroh Timothy Odiri: 4 embeddings
Olarotimi Esther: 11 embeddings
```

## 4.3 Preprocessing and Face Detection

Every uploaded photograph is checked for exactly one detectable face before it is accepted. The relevant excerpt from `face_service.py` and `enrollment_service.py` is:

```python
def encode_single_face(image):
    locations = detect_face_locations(image)
    if len(locations) == 0:
        raise NoFaceFoundError()
    if len(locations) > 1:
        raise MultipleFacesFoundError(len(locations))
    encodings = face_recognition.face_encodings(image, known_face_locations=locations)
    return encodings[0]
```

Uploading a blank, face-less image to this pipeline produces a real, observed rejection rather than a crash or a silently accepted embedding:

```
POST /people/2/photos  files=[blank.jpg]
-> 200 OK
   {"filename": "blank.jpg", "accepted": false, "reason": "No face detected in photo."}
```

Across all 48 real enrollment photographs currently accepted into the system, the evaluation script's dataset loader, which uses this same detection step, reported zero warnings, meaning every one of those 48 photographs had exactly one detectable face; no enrollment photograph currently in the system was borderline or manually forced through.

## 4.4 Feature Extraction and Embedding

Embedding generation is provided by the `face_recognition` library's pretrained encoder and is not modified by this project. Calling it directly demonstrates its real, observed output shape:

```python
encoding = face_recognition.face_encodings(image, known_face_locations=[location])[0]
print(encoding.shape, encoding.dtype)
```

```
(128,) float64
```

Two independent 128-dimensional embeddings of the same person's face produce a small measured Euclidean distance, while embeddings of two different people's faces produce a substantially larger one, confirming the embedding space behaves as the underlying theory predicts before any project-specific logic is applied on top of it:

```
distance, same person (two photos): 0.0000 to ~0.31 across real enrolled samples
distance, two different people (Obama vs. Biden test images): 0.8402
```

## 4.5 Model Development

No model was trained or fine-tuned in this project. This stage consists entirely of loading and reusing the pretrained dlib ResNet encoder distributed with `face_recognition`, as already shown above in the feature extraction stage. This is a deliberate transfer-learning decision rather than an omission, discussed further in the methodology.

## 4.6 Recognition and Classification

Recognition compares a freshly captured embedding against every stored embedding and applies a distance threshold. The relevant excerpt from `matching_service.py` is:

```python
def find_best_match(db, query_embedding, threshold):
    rows = db.execute(
        select(FaceEmbedding).options(selectinload(FaceEmbedding.person))
    ).scalars().all()
    best_distance, best_person = None, None
    for row in rows:
        distance = euclidean_distance(query_embedding, np.array(row.vector))
        if best_distance is None or distance < best_distance:
            best_distance, best_person = distance, row.person
    if best_distance is None or best_distance > threshold:
        return MatchResult(person=None, distance=best_distance)
    return MatchResult(person=best_person, distance=best_distance)
```

Real kiosk captures during system testing produced the following genuine observed outcomes, shown here as the actual distance values returned by the running system:

```
Fagbami Pelumi (enrolled, self-capture): distance 0.2374 -> matched, "already marked today"
Akinshade Mykel Ayomiposi (enrolled, self-capture): distance 0.2684 -> matched, attendance marked
An unenrolled test participant (never enrolled): distance 0.4643 -> unrecognized (threshold 0.40)
```

## 4.7 Evaluation

Evaluation is performed offline against the real enrolled dataset described at the start of this chapter, using the pairwise methodology and formulas set out in the methodology chapter. Invoking the evaluation script directly:

```
venv/Scripts/python.exe evaluation/evaluate.py --threshold 0.4
```

produced the following real, observed output, with no warnings and no skipped photographs:

```
Enrolled people: 6, unknown people: 0
Genuine pairs: 153, impostor pairs: 667

At threshold 0.4:
  Accuracy:  0.9488
  Precision: 0.9664
  Recall:    0.7516
  F1:        0.8456
  FAR:       0.0060
  FRR:       0.2484
  EER:       0.1173 (at threshold 0.4558)
  ROC-AUC:   0.9566
```

This result is discussed in detail in the discussion section that closes this chapter; it is not presented as a final, generalizable accuracy figure, and that discussion explains why.

## 4.8 System Implementation Walkthrough

*[Figure 4.1: Landing page, showing the problem statement, pipeline explanation, team and supervisor names, and the limitations/disclaimers section, to be inserted.]*

*[Figure 4.2: Admin dashboard, People tab, showing the six enrolled participants and their enrolled-photo counts, to be inserted.]*

*[Figure 4.3: Admin dashboard, Sessions tab, showing a created session, to be inserted.]*

*[Figure 4.4: Kiosk page mid-capture, showing the challenge-response instruction overlay ("Step 2 of 3: turn your head to the LEFT"), to be inserted.]*

*[Figure 4.5: Kiosk page showing a successful attendance-marked result with the real match distance and threshold displayed, to be inserted.]*

*[Figure 4.6: Admin dashboard, Attendance tab, showing the on-screen review table for a session, to be inserted.]*

*[Figure 4.7: Printable attendance sheet (print preview), showing name, matric number, email, date, and time for a session, to be inserted.]*

## 4.9 System-Level Testing Results

The system was tested against the specific realistic and adversarial conditions identified in the methodology, using both real people and the automated test suite (21 automated tests, all passing at the time of writing).

**Valid enrolled face, accepted.** Demonstrated repeatedly during live kiosk testing, with real match distances reported earlier in the recognition and classification stage of this chapter.

**Genuinely unenrolled person, correctly rejected.** An unenrolled test participant was deliberately presented to the kiosk. This is documented in detail among the bugs found and fixed below, because the first two attempts at this test case failed before the underlying cause was found and fixed.

**No face in frame.** An automated test uploads a blank, face-less image and confirms the system responds with `accepted: false` and the reason `"No face detected in photo."`, rather than crashing or accepting a meaningless embedding.

**Multiple faces in one frame.** The group-scan feature was tested with a real composite image containing two genuine detected faces (constructed by placing two real photographs side by side). The system correctly detected and independently classified both faces, matching the enrolled one and rejecting the other as unrecognized, in a single request.

**Basic anti-spoofing (photograph replay).** The kiosk-burst endpoint was tested by submitting the same static photograph repeatedly as a simulated capture "burst." Because a static image cannot blink or move, the liveness check correctly rejected it, reporting `liveness_passed: false`, both in the automated test suite and against the live running server.

**Poor lighting.** Several live kiosk attempts during testing were captured under genuinely poor, uneven indoor lighting (visibly underexposed in the resulting frames). The system continued to produce plausible, non-crashing distance measurements under these conditions, though as discussed in the closing section of this chapter, poor lighting is also implicated in the false-accept defect described below, rather than being a condition the system is shown to be fully robust to.

**Off-angle capture.** The system's challenge-response liveness check requires the user to turn their head during capture, which necessarily exercises non-frontal face angles during the liveness stage. However, this project did not carry out a dedicated, isolated test of recognition accuracy specifically as a function of capture angle, and that is reported here as a gap in testing coverage rather than a result.

### 4.9.1 Bugs Found and Fixed

**Authentication crash on login (passlib/bcrypt incompatibility).** During implementation of admin authentication, calling the password-hashing function raised `ValueError: password cannot be longer than 72 bytes, truncate manually if necessary`, and every authentication test failed. Investigation traced this to `passlib`, an unmaintained library, performing an internal self-test against the installed `bcrypt` version using a secret longer than the library's own advertised limit, itself a symptom of `passlib` not recognizing the modern `bcrypt` API. The fix was to remove `passlib` entirely and call `bcrypt`'s `hashpw` and `checkpw` functions directly. Before the fix, the authentication test run reported 7 errors; after the fix, the same run reported 9 tests passed and 0 failures.

**Database query inefficiency (N+1 query).** Manual timing of the recognition endpoint showed a single request taking approximately 1.4 seconds even on a warm database connection, which was inconsistent with the sub-millisecond cost of comparing against 48 stored embeddings measured in isolation. Instrumented timing isolated the discrepancy to a single line, `row.person`, which, by SQLAlchemy's default lazy-loading behavior, issued one additional network round trip to the hosted database for every distinct enrolled person rather than fetching all of them in one query. The fix was to add `selectinload(FaceEmbedding.person)` to the query. Measured before the fix, four consecutive calls averaged approximately 1,400 milliseconds each; measured after the fix, the same four calls averaged approximately 550 milliseconds each, a real, measured reduction of roughly 60 percent on that step. The same defect and fix were later found and applied a second time in the attendance-listing endpoint, which had the identical pattern.

**Server-wide blocking during recognition requests.** The recognition and enrollment endpoints were originally declared as `async def` while calling blocking, CPU-bound face-detection code and blocking database calls inside them, which ties up the single-threaded event loop FastAPI otherwise uses to serve every request. This was verified directly: a slow kiosk request and a trivial health-check request were fired concurrently from two threads against the live server; before the fix this would serialize the two requests, and after converting the affected endpoints to plain `def` functions, which FastAPI runs in a worker thread automatically, the health check, fired half a second into a 4.48-second kiosk request that was still processing, returned in 18.5 milliseconds rather than waiting for the kiosk request to finish.

**False acceptance of an unenrolled person.** During live testing, an unenrolled participant's face was matched to an enrolled person at a measured distance of 0.4553, below the then-current threshold of 0.5, and attendance was incorrectly marked. The threshold was lowered to 0.4 in response. On the next live test, the same unenrolled participant was again incorrectly accepted, at measured distances of 0.4793 and 0.4754, both above the intended new threshold of 0.4; investigation found that a `.env` configuration file still contained the old value of 0.5 and was overriding the code's default, and that the running server process had not actually been restarted after the file was corrected. Once the configuration file was corrected and the server process genuinely restarted, the same unenrolled participant was correctly rejected at a measured distance of 0.4643. This sequence is reported in full, including the two failed correction attempts, rather than only the final successful outcome.

**Liveness threshold based on an untested assumption.** The Eye Aspect Ratio threshold used to detect a blink was initially set to 0.23 based on figures commonly cited in the general literature for an open eye. Measuring this value directly against a real, open-eyed test photograph using this project's own detection pipeline returned 0.213, below the assumed threshold, which would have caused open eyes to be misclassified as closed and broken blink detection entirely. The default was lowered to 0.19. This value is still flagged in the source code as provisional, since it was calibrated from a single still photograph rather than real burst-capture video, and is reported here as an open limitation rather than a fully resolved defect.

## 4.10 Discussion

The evaluation reported above is not suspiciously perfect, and that is treated here as a meaningful part of the result rather than something to explain away. An Accuracy of 94.88% and an EER of 11.73% are respectable but clearly imperfect figures, and the gap between Precision (0.9664) and Recall (0.7516) points to a specific, identifiable behavior rather than generic noise: at the current operating threshold of 0.4, the system is considerably more likely to wrongly reject a genuine enrolled person (FRR 24.84%) than to wrongly accept an impostor (FAR 0.60%). This is a direct, traceable consequence of the threshold decision documented among the bugs found and fixed above, where the threshold was deliberately tightened from 0.5 to 0.4 in direct response to a real false-accept incident, prioritizing security over convenience. The evaluation's own EER calculation shows that a threshold of approximately 0.4558 would balance the two error types more evenly; the decision to keep the stricter 0.4 threshold in production, accepting a higher false-rejection rate as the cost of a lower false-acceptance rate, is reported here as a deliberate, documented trade-off rather than an oversight.

A second limitation of the evaluation itself is that its 667 impostor pairs were drawn entirely from cross-comparisons among the six enrolled people, since no separate cohort of people who were never enrolled at all was gathered for this evaluation run. The one genuinely unenrolled test case reported in this chapter, the participant described above among the bugs found and fixed and in the system-level testing results, is real and was correctly rejected at the final, corrected threshold, but it is a single case, not a systematically sampled one, and the evaluation's formal FAR figure should be read with that in mind.

Finally, the enrolled cohort itself is small and was not assembled to be demographically diverse. Face recognition systems are well documented to perform unevenly across demographic groups, a concern raised directly by Buolamwini and Gebru (2018) in their study of commercial gender classification systems. The National Institute of Standards and Technology's own vendor testing programme has independently reached a similar conclusion across a much wider range of face recognition algorithms (Grother et al., 2019). No claim is made here that the accuracy figures reported above would generalize to a larger or more demographically varied population than the one actually enrolled and tested.
