from band.matchmaking.types import Player, Discipline, FEMALE

LEVEL_SCORE = {
    "master": 7, "s": 6, "a": 5, "b": 4, "c": 3, "d": 2, "beginner": 1,
}


def level_to_score(level: str) -> int:
    return LEVEL_SCORE.get((level or "").lower(), 1)


def effective_score(player: Player, discipline: Discipline, female_adjust: int = 1) -> int:
    base = player.base_level
    if discipline == Discipline.MIXED and player.gender == FEMALE:
        return max(1, base - female_adjust)
    return base
