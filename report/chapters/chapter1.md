# CHAPTER ONE

# INTRODUCTION

## 1.1 Background of the Study

Attendance taking remains one of the most routine yet consequential administrative tasks in academic institutions. In most departments it is still done by roll call or by passing round a paper register, a method that consumes lecture time, depends entirely on the honesty of the person marking it, and leaves a record that is tedious to audit after the fact. It is also easy to falsify by proxy, where a present student answers or signs on behalf of an absent one, a weakness that manual and paper-based systems have little practical means of detecting.

Advances in deep learning have made automated face recognition a realistic alternative to these manual methods. Modern face recognition systems no longer rely on hand-crafted features; instead, a convolutional neural network is trained to map a face image to a compact numerical vector, commonly called an embedding, such that images of the same person produce vectors that are close together while images of different people produce vectors that are far apart (El Fadel, 2025). This embedding-based approach underlies most face recognition and face verification systems in current use, and it is the same underlying principle this project relies on for enrollment and recognition.

The specific application of this technology to classroom attendance is itself an active area of recent research rather than a settled, solved problem. Thalor and Gaikwad (2024) describe a deep-learning-based attendance monitoring system that captures a classroom image, detects faces, and verifies them against a stored database before logging attendance automatically, reporting the approach as substantially faster than manual roll call. Similar systems reviewed across the literature emphasize automatic, real-time attendance capture as their central motivation, treating older methods such as manual registers and even earlier technologies like barcode or RFID cards as insufficiently fast or secure for present classroom needs.

At the same time, an honest treatment of face recognition cannot ignore two well-documented limitations that recent literature continues to raise. The first is that recognition accuracy is not uniform across all users. Buolamwini and Gebru (2018) showed that several commercial face classification systems performed markedly worse on darker-skinned and female faces than on lighter-skinned male faces, and the National Institute of Standards and Technology's Face Recognition Vendor Test has since documented similar demographic accuracy differences across a wide range of face recognition algorithms (Grother et al., 2019). The second limitation is that a face recognition system that only asks "does this face match an enrolled face" is vulnerable to being shown a photograph or a video of an enrolled person rather than the person themselves. Addressing this requires a liveness or anti-spoofing check, and this is itself an active research area: Keresh and Shamoi (2024) apply self-supervised transformer models to distinguish a live capture from a spoofed one, while Kuznetsov et al. (2025) survey deep learning approaches to facial liveness detection more broadly and note that no current method is completely immune to a sufficiently determined attacker.

This project sits deliberately inside these constraints rather than around them. It does not train a new face recognition model from scratch, an undertaking that would require far more data and compute than is realistic within a final year project timeframe. Instead, it builds an attendance system from proven, well-documented, pretrained components, specifically the `face_recognition` Python library, which wraps a dlib ResNet encoder for face detection and embedding generation, and it treats the demographic and spoofing limitations described above as things to test for and disclose honestly rather than to assume away.

## 1.2 Problem Statement

Manual attendance taking in the department is slow relative to class size, is not resistant to proxy attendance, and produces records that are difficult to verify or audit after a class has ended. Existing published face-recognition-based attendance systems demonstrate that automated recognition can address the speed and record-keeping problems (Thalor & Gaikwad, 2024), but a system that only checks "is this a known face" without any liveness safeguard has not actually solved proxy attendance, since a photograph of an enrolled student would satisfy that check just as easily as the student's real presence. There is, therefore, a need for an attendance system that combines automated face recognition with a genuine liveness check, that is built from components realistic to implement and evaluate within a final year project, and that is tested and reported on honestly, including its failure cases, rather than presented only through its best-case results.

## 1.3 Aim and Objectives

The aim of this study is to design, implement, and evaluate an AI-based attendance system that uses face recognition and a liveness check to automate classroom attendance taking.

The specific objectives of the study are to:

i. design and implement a consent-based enrollment pipeline that captures multiple reference photographs of each participant and generates a face embedding for each accepted photograph using a pretrained deep learning encoder;

ii. implement a recognition and attendance-logging pipeline that detects a face from a live camera capture or an uploaded photograph, compares it against enrolled embeddings by distance, and logs attendance once per person per session while correctly rejecting an unenrolled face rather than assigning it to the nearest enrolled identity;

iii. implement a challenge-response liveness check, requiring a detected blink or a specific head movement during capture, as a basic safeguard against a static photograph being presented in place of a live person;

iv. evaluate the system's recognition performance using standard face-verification metrics, namely Accuracy, Precision, Recall, F1-score, and ROC-AUC, together with the face-recognition-specific metrics False Acceptance Rate, False Rejection Rate, and Equal Error Rate;

v. test the system under realistic, non-ideal operating conditions, including poor lighting, an off-angle capture, an absence of any face in frame, multiple faces in a single frame, and a basic photograph-replay spoofing attempt, and document any defects this testing uncovers together with how each was fixed; and

vi. provide an administrative dashboard through which enrolled participants and attendance records for a given session can be reviewed and printed.

## 1.4 Research Questions

The study seeks to answer the following questions:

i. To what extent can a face recognition pipeline built from existing pretrained components, rather than a model trained from scratch, reliably distinguish an enrolled person from an unenrolled one under real, uncontrolled capture conditions?

ii. What are the system's measured Accuracy, Precision, Recall, F1-score, ROC-AUC, False Acceptance Rate, False Rejection Rate, and Equal Error Rate when evaluated on genuine and impostor face samples?

iii. Can a lightweight challenge-response liveness check meaningfully reduce the system's susceptibility to a basic photograph-replay spoofing attempt without adding excessive time or complexity to the attendance-taking process?

iv. What practical defects or limitations arise when the system is tested under realistic, non-ideal conditions, and how can these be identified and resolved?

## 1.5 Significance of the Study

To the department, the study offers a working demonstration of an attendance method that is faster than manual roll call and considerably more resistant to proxy attendance than either manual registers or a face recognition system without a liveness check. To future students undertaking similar projects, it offers a documented account of what actually happens when pretrained face recognition components are integrated into a full system and tested honestly, including the real defects encountered along the way, rather than an idealized description of a system that is assumed to work. To the wider discussion around face recognition technology, the study contributes a small but transparent case study that explicitly measures and reports its own error rates and limitations instead of presenting face recognition as a solved problem.

## 1.6 Scope of the Study

The study covers the design, implementation, and evaluation of a face-recognition-based attendance system intended for a single class or department rather than an institution-wide deployment. The system was built using a FastAPI backend, a React frontend, and a PostgreSQL database, with face detection and embedding generation provided by the `face_recognition` Python library. Enrollment and evaluation were carried out on a small cohort of consenting participants, comprising the project researchers and consenting classmates, rather than a large or demographically balanced population. Liveness detection is limited to blink detection and coarse head-movement detection and is not presented as a security-grade anti-spoofing solution. Testing was carried out on the researchers' own computers and webcams rather than on fixed, institution-owned hardware.

## 1.7 Limitations of the Study

The system was evaluated on a small, non-diverse enrolled dataset gathered from the researchers and a limited number of consenting classmates. Face recognition systems are well documented to perform unevenly across lighting conditions, skin tones, and demographic groups, a disparity Buolamwini and Gebru (2018) demonstrated directly in commercial gender classification systems. The National Institute of Standards and Technology has since reported similar demographic accuracy differences across a wide range of face recognition algorithms in its own vendor testing (Grother et al., 2019). A dataset of this size and composition cannot support a claim that the system's measured accuracy would generalize to a larger or more diverse population. The liveness check implemented in this study is a basic, passive-to-active anti-spoofing measure and is not a security-grade liveness system; it is not intended to resist a determined attacker using, for example, a pre-recorded video that already contains the requested action. The system was also evaluated against a free-tier hosted database, which introduces an occasional multi-second connection delay after a period of inactivity that is a property of the hosting tier rather than of the recognition pipeline itself. Finally, as with any project of this scope and timeframe, the evaluation reflects the specific enrolled cohort, hardware, and testing conditions used during development, and results obtained under different conditions may differ.

## 1.8 Definition of Terms

**Face Detection**: the process of locating the position of a face, if any, within an image or video frame, without identifying who the face belongs to.

**Face Recognition / Face Verification**: the process of determining whether a detected face matches a specific previously enrolled identity, typically by comparing numerical representations of the faces rather than the raw images.

**Face Embedding**: a fixed-length numerical vector produced by a neural network from a face image, constructed so that vectors from images of the same person are close together and vectors from images of different people are far apart.

**Enrollment**: the process of registering a person into the system by capturing reference photographs of their face and generating and storing the corresponding embeddings.

**Liveness Detection (Anti-Spoofing)**: a check intended to confirm that a face presented to the system belongs to a live person physically present at the camera, rather than a photograph, screen replay, or other artificial presentation.

**False Acceptance Rate (FAR)**: the proportion of impostor comparisons, that is, comparisons between two different people's faces, that are incorrectly accepted as a match.

**False Rejection Rate (FRR)**: the proportion of genuine comparisons, that is, comparisons between two images of the same enrolled person, that are incorrectly rejected as not matching.

**Equal Error Rate (EER)**: the error rate at the specific decision threshold where the False Acceptance Rate and False Rejection Rate are equal.

**ROC-AUC**: the area under the Receiver Operating Characteristic curve, a threshold-independent summary of how well a system separates genuine from impostor comparisons across all possible decision thresholds.

**Transfer Learning**: the practice of reusing a neural network that has already been trained on a large dataset for a related task, rather than training a new network from randomly initialized weights.

**Challenge-Response**: a liveness verification approach in which the system issues an instruction, such as asking the person to blink or turn their head in a specific direction, and verifies that the requested action was actually performed during capture.
