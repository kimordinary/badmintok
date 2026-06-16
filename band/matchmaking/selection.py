from band.matchmaking.types import Player

NEVER_PLAYED = float("-inf")  # 동률 시 가장 앞으로


def queue_order(players: list[Player]) -> list[Player]:
    def key(p: Player):
        rested_marker = p.last_game_ended_at if p.last_game_ended_at is not None else NEVER_PLAYED
        return (p.total_games, rested_marker)
    return sorted(players, key=key)
