# SynapseLearn PRD

## Original problem statement
hey i want to build an adaptive learning website that includes from the opening page of the website the should have all the login details and after logging in the user should have different different subjects to study, learn and then after the user has finished studying the user should get quizes based on the subject and for every right or wrong answer there should be an explanation like based on each users understanding and each users memory the notes and quizez should be made easily understandable

## Architecture decisions
- React single-page learning experience, FastAPI `/api` service, MongoDB persistence.
- JWT email authentication plus a Google sign-in entry point; AI explanations use Emergent LLM key and GPT 5.6 Luna.
- Subject and lesson content has a deterministic seed so the first experience is useful even before personalization history exists.

## Users and requirements
- School learners selecting a grade and age, needing clear lessons and kind feedback.
- Core flow: login/register → subject library → lesson → adaptive quiz → explanation → progress.

## Implemented (2026-08-27)
- SynapseLearn dark/light editorial interface, responsive navigation, subject library, daily goal, streak and progress views.
- Email/password register/login API, Google demo sign-in route, lesson and quiz endpoints.
- Personalized tutor explanation endpoint using GPT 5.6 Luna streaming integration with safe fallback.
- All key UI controls and information surfaces include unique data-testid attributes.
- Every subject now has a basic summary and instant fallback lesson content.
- Quizzes now contain five capacity-check questions with simple explanations per answer.
- Quiz attempts are saved to MongoDB and feed the review queue and concept-level progress insights.
- Each subject lesson now includes nine memorable points with a summary and example.
- Quiz sessions now show five questions, per-question explanations, score percentage, performance guidance, and a concept breakdown.
- Lesson, quiz, and score views include browser fullscreen controls with an exit action.

## Backlog
- P0: Add Google OAuth Client ID and Secret, then replace the demo endpoint with the verified OAuth callback.
- P1: Grade-specific lesson library and diagnostic onboarding.
- P2: Parent/teacher view, accessibility reading mode, downloadable progress report.