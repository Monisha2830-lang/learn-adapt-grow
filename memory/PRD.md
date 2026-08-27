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

## Implemented (2026-10-14)
- SynapseLearn dark/light editorial interface, responsive navigation, subject library, daily goal, streak and progress views.
- Email/password register/login API, Google demo sign-in route, lesson and quiz endpoints.
- Personalized tutor explanation endpoint using GPT 5.6 Luna streaming integration with safe fallback.
- All key UI controls and information surfaces include unique data-testid attributes.

## Backlog
- P0: Persist quiz attempts and per-user study history; implement real Google OAuth callback.
- P1: Grade-specific lesson library, diagnostic onboarding, spaced-repetition review queue.
- P2: Parent/teacher view, accessibility reading mode, downloadable progress report.