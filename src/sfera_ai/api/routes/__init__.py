from fastapi import APIRouter

from sfera_ai.api.routes import candidates, vacancy

# 03_TDD.md, «3. API / контракты» — неймспейс, не пересекающийся с существующими
# сериализаторами кандидата в sfera_backend. Эндпоинты добавляются следующими
# шагами эпика E8.
router = APIRouter(prefix="/api/v1/courses/{course_uuid}/ai-analysis", tags=["ai-analysis"])
router.include_router(candidates.router)
router.include_router(vacancy.router)
