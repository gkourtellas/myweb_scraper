import argparse
import json
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List


@dataclass
class BotConfig:
    dry_run: bool
    bankroll: float
    stake: float
    min_back_odds: float
    max_back_odds: float
    max_open_bets: int
    max_session_loss: float
    max_total_exposure: float


@dataclass
class MarketSnapshot:
    market_id: str
    selection: str
    back_odds: float
    lay_odds: float
    result: str


@dataclass
class Bet:
    market_id: str
    selection: str
    odds: float
    stake: float
    pnl: float


class RiskGuard:
    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def can_place(
        self,
        open_bets: int,
        total_exposure: float,
        session_pnl: float,
    ) -> bool:
        if open_bets >= self.config.max_open_bets:
            print("[RISK] Blocked: max open bets reached")
            return False

        if total_exposure + self.config.stake > self.config.max_total_exposure:
            print("[RISK] Blocked: max total exposure reached")
            return False

        if session_pnl <= -abs(self.config.max_session_loss):
            print("[RISK] Blocked: max session loss reached")
            return False

        return True


class SimpleBot:
    def __init__(self, config: BotConfig, snapshots: List[MarketSnapshot]) -> None:
        self.config = config
        self.snapshots = snapshots
        self.guard = RiskGuard(config)
        self.bets: List[Bet] = []
        self.session_pnl = 0.0
        self.events: List[str] = []

    def _log(self, message: str) -> None:
        self.events.append(message)
        print(message)

    def run(self) -> Dict[str, Any]:
        if not self.config.dry_run:
            raise RuntimeError(
                "Live mode is disabled in V1. Use dry_run=true until official API credentials are added."
            )

        self._log("[START] Running in paper mode")

        for snap in self.snapshots:
            if self.session_pnl <= -abs(self.config.max_session_loss):
                self._log("[STOP] Session loss limit hit")
                break

            if not self._is_entry_signal(snap):
                self._log(f"[SKIP] {snap.market_id} {snap.selection}: odds out of range")
                continue

            open_bets = 0
            exposure = sum(b.stake for b in self.bets)
            if not self.guard.can_place(open_bets, exposure, self.session_pnl):
                continue

            bet = self._place_paper_bet(snap)
            self.bets.append(bet)
            self.session_pnl += bet.pnl

            self._log(
                f"[BET] {bet.market_id} {bet.selection} @ {bet.odds:.2f} stake={bet.stake:.2f} pnl={bet.pnl:.2f}"
            )

        return self._build_result()

    def _is_entry_signal(self, snap: MarketSnapshot) -> bool:
        return self.config.min_back_odds <= snap.back_odds <= self.config.max_back_odds

    def _place_paper_bet(self, snap: MarketSnapshot) -> Bet:
        if snap.result.lower() == "win":
            pnl = (snap.back_odds - 1.0) * self.config.stake
        else:
            pnl = -self.config.stake

        return Bet(
            market_id=snap.market_id,
            selection=snap.selection,
            odds=snap.back_odds,
            stake=self.config.stake,
            pnl=round(pnl, 2),
        )

    def _build_result(self) -> Dict[str, Any]:
        wins = len([b for b in self.bets if b.pnl > 0])
        losses = len([b for b in self.bets if b.pnl < 0])
        roi = (self.session_pnl / self.config.bankroll) * 100 if self.config.bankroll else 0

        summary = {
            "bets": len(self.bets),
            "wins": wins,
            "losses": losses,
            "session_pnl": round(self.session_pnl, 2),
            "roi_pct": round(roi, 2),
        }

        self._log("")
        self._log("[SUMMARY]")
        self._log(f"bets={summary['bets']} wins={summary['wins']} losses={summary['losses']}")
        self._log(f"session_pnl={summary['session_pnl']:.2f}")
        self._log(f"roi_pct={summary['roi_pct']:.2f}")

        return {
            "summary": summary,
            "bets": [asdict(b) for b in self.bets],
            "events": self.events,
        }


def load_config(path: Path) -> BotConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    return BotConfig(**data)


def load_markets(path: Path) -> List[MarketSnapshot]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [MarketSnapshot(**item) for item in raw]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple Matchbook paper bot")
    parser.add_argument("--config", required=True, help="Path to config JSON")
    parser.add_argument("--markets", required=True, help="Path to market snapshots JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config))
    snapshots = load_markets(Path(args.markets))

    bot = SimpleBot(config, snapshots)
    bot.run()


if __name__ == "__main__":
    main()
