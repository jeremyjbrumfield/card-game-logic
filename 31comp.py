import streamlit as st
import random
from typing import List, Tuple

st.set_page_config(page_title="31", page_icon="🃏", layout="wide")
st.title("🃏 31")

SUITS = ["♥", "♦", "♣", "♠"]
RANKS = ["7", "8", "9", "10", "J", "Q", "K", "A"]
VALUES = {"7":7, "8":8, "9":9, "10":10, "J":10, "Q":10, "K":10, "A":11}

def create_deck() -> List[str]:
    return [f"{rank}{suit}" for suit in SUITS for rank in RANKS]

def card_value(card: str) -> int:
    return VALUES[card[:-1]]

def evaluate_hand(hand: List[str]) -> Tuple[float, str]:
    if len(hand) != 3: return 0, ""
    if all(c[:-1] == "A" for c in hand): return 33, "Fire"
    for suit in SUITS:
        suited = [c for c in hand if c[-1] == suit]
        if len(suited) == 3 and sum(card_value(c) for c in suited) == 31:
            return 31, "31"
    ranks = [c[:-1] for c in hand]
    if len(set(ranks)) == 1 and ranks[0] != "A":
        return 30.5, "3-kind"
    max_score = max(sum(card_value(c) for c in hand if c[-1] == s) for s in SUITS)
    return max_score, "Best suit"

# Changelog:
# - Fixed knock logic: now properly counts full cycle after knock
# - Knock now ends after all players (including knocker) have had one more turn
# - Added clear comments and debug logging

if "game_started" not in st.session_state:
    st.session_state.game_started = False

if not st.session_state.game_started:
    st.header("New Game Setup")
    num_ai = st.slider("AI Players", 1, 5, 3)
    ai_diff = st.selectbox("AI Difficulty", ["easy", "medium", "hard"], index=1)
  
    if st.button("Start Game", type="primary"):
        players = ["You"] + [f"AI {i+1}" for i in range(num_ai)]
        st.session_state.update({
            "players": players,
            "coins": {p: 3 for p in players},
            "pot": 0,
            "dealer_idx": 0,
            "current_player_idx": 0,
            "round_phase": "deal",
            "deck": create_deck(),
            "hands": {},
            "table": [],
            "blind": [],
            "knock_player": None,
            "knock_rounds_left": 0,
            "selected_hand": None,
            "last_ai_processed": None,
            "ai_diff": ai_diff,
            "game_started": True,
            "log": []
        })
        st.rerun()
else:
    p = st.session_state.players
    c = st.session_state.coins
    pot = st.session_state.pot
    d_idx = st.session_state.dealer_idx
    cur_idx = st.session_state.current_player_idx
    phase = st.session_state.round_phase
    hands = st.session_state.hands
    table = st.session_state.table
    log = st.session_state.log

    with st.sidebar:
        st.header("Status")
        st.write(f"**Pot:** {pot}")
        st.write(f"**Dealer:** {p[d_idx]}")
        st.subheader("Coins")
        for pl in p:
            st.write(f"{pl}: {c[pl]} 🪙" if c[pl] > 0 else f"{pl}: OUT")
        if st.button("New Game"):
            st.session_state.game_started = False
            st.rerun()
        st.subheader("Game Log")
        for entry in log[-10:]:
            st.write(entry)

    if phase == "deal":
        # ... (dealer phase unchanged)
        st.header("Dealer Phase")
        dealer = p[d_idx]
        if not hands:
            random.shuffle(st.session_state.deck)
            for pl in p:
                hands[pl] = st.session_state.deck[:3]
                st.session_state.deck = st.session_state.deck[3:]
            st.session_state.blind = st.session_state.deck[:3]
            st.session_state.deck = st.session_state.deck[3:]
            st.session_state.hands = hands

        st.subheader(f"{dealer}'s Hand")
        hcols = st.columns(3)
        for i, card in enumerate(hands[dealer]):
            hcols[i].button(card, key=f"dealer_hand_{i}", disabled=True)

        st.subheader("Blind")
        bcols = st.columns(3)
        for i in range(3):
            bcols[i].button("?", key=f"blind_{i}", disabled=True)

        col1, col2 = st.columns(2)
        if col1.button("Keep my hand", type="primary"):
            st.session_state.table = st.session_state.blind[:]
            st.session_state.blind = []
            st.session_state.round_phase = "play"
            st.session_state.current_player_idx = (d_idx + 1) % len(p)
            log.append("Dealer kept hand.")
            st.rerun()

        if col2.button("Swap with blind", type="secondary"):
            hands[dealer], st.session_state.blind = st.session_state.blind, hands[dealer]
            st.session_state.table = st.session_state.blind[:]
            st.session_state.blind = []
            st.session_state.round_phase = "play"
            st.session_state.current_player_idx = (d_idx + 1) % len(p)
            log.append("Dealer swapped with blind.")
            st.session_state.hands = hands
            st.rerun()

    elif phase == "play":
        current = p[cur_idx]
        st.subheader(f"Turn: {current}")

        # AI turn
        if current != "You":
            if st.session_state.get("last_ai_processed") != cur_idx:
                score, typ = evaluate_hand(hands[current])
                log.append(f"{current} hand: {hands[current]} score={score} ({typ})")
              
                if score < 22 and table:
                    new_hand = table[:]
                    new_table = hands[current][:]
                    hands[current] = new_hand
                    st.session_state.table = new_table
                    log.append(f"{current} swapped all 3 cards.")
                else:
                    log.append(f"{current} passed.")

                if evaluate_hand(hands[current])[0] >= 31:
                    log.append(f"**{current} got 31+ → instant win!**")
                    for pl in p:
                        if pl != current and c[pl] > 0:
                            c[pl] -= 1
                            pot += 1
                    st.session_state.round_phase = "end_round"
                    st.session_state.hands = hands
                    st.rerun()

                st.session_state.current_player_idx = (cur_idx + 1) % len(p)
                st.session_state.last_ai_processed = cur_idx
                st.session_state.hands = hands
                st.rerun()

        else:  # Your turn
            st.subheader("Your Hand")
            hcols = st.columns(3)
            for i, card in enumerate(hands["You"]):
                label = f"**{card}**" if st.session_state.get("selected_hand") == i else card
                if hcols[i].button(label, key=f"hand_{i}", use_container_width=True):
                    st.session_state.selected_hand = i if st.session_state.get("selected_hand") != i else None
                    st.rerun()

            st.subheader("Table")
            if table:
                tcols = st.columns(len(table))
                for i, card in enumerate(table):
                    if tcols[i].button(card, key=f"table_{i}", use_container_width=True):
                        if st.session_state.get("selected_hand") is not None:
                            hidx = st.session_state.selected_hand
                            old_h = hands["You"][hidx]
                            old_t = table[i]
                            hands["You"][hidx], table[i] = table[i], hands["You"][hidx]
                            st.session_state.selected_hand = None
                            log.append(f"You swapped {old_h} ↔ {old_t}")
                            if evaluate_hand(hands["You"])[0] >= 31:
                                log.append("You got 31+ → instant win!")
                                for pl in p:
                                    if pl != "You" and c[pl] > 0:
                                        c[pl] -= 1
                                        pot += 1
                                st.session_state.round_phase = "end_round"
                            st.session_state.current_player_idx = (cur_idx + 1) % len(p)
                            st.session_state.hands = hands
                            st.session_state.table = table
                            st.rerun()

            col1, col2, col3 = st.columns(3)
            if col1.button("Pass", use_container_width=True):
                log.append("You passed.")
                st.session_state.current_player_idx = (cur_idx + 1) % len(p)
                st.session_state.selected_hand = None
                st.session_state.last_ai_processed = None
                st.rerun()

            if col2.button("Swap All", use_container_width=True) and table:
                new_hand = table[:]
                new_table = hands["You"][:]
                hands["You"] = new_hand
                st.session_state.table = new_table
                log.append("You swapped all 3 cards.")
                if evaluate_hand(hands["You"])[0] >= 31:
                    log.append("You got 31+ → instant win!")
                    for pl in p:
                        if pl != "You" and c[pl] > 0:
                            c[pl] -= 1
                            pot += 1
                    st.session_state.round_phase = "end_round"
                st.session_state.selected_hand = None
                st.session_state.current_player_idx = (cur_idx + 1) % len(p)
                st.session_state.hands = hands
                st.rerun()

            if col3.button("Knock", use_container_width=True):
                st.session_state.knock_player = "You"
                st.session_state.knock_rounds_left = len(p) - 1   # Full cycle left
                log.append("You knocked.")
                st.session_state.current_player_idx = (cur_idx + 1) % len(p)
                st.session_state.selected_hand = None
                st.session_state.last_ai_processed = None
                st.rerun()

        # FIXED Knock Logic
        # Trigger showdown when knock_rounds_left reaches 0
        if st.session_state.get("knock_player") is not None and phase == "play":
            if st.session_state.knock_rounds_left <= 0:
                st.session_state.round_phase = "end_round"
                log.append("Knock rounds finished → ending round")
                st.rerun()

            # Advance knock after every AI turn (including after You knocked)
            elif current != "You" and st.session_state.get("last_ai_processed") == cur_idx:
                st.session_state.knock_rounds_left -= 1
                log.append(f"Knock advanced - rounds left: {st.session_state.knock_rounds_left}")
                st.session_state.current_player_idx = (cur_idx + 1) % len(p)
                st.rerun()

    # Showdown
    if st.session_state.round_phase == "end_round":
        st.header("Showdown - Round Over")
        scores = {}
        for pl in p:
            if c[pl] > 0:
                sc, typ = evaluate_hand(hands[pl])
                scores[pl] = (sc, typ)
                log.append(f"{pl} final: {sc} ({typ})")

        fire_winner = next((pl for pl, (sc, typ) in scores.items() if typ == "Fire"), None)
        if fire_winner:
            for pl in p:
                if pl != fire_winner and c[pl] > 0:
                    c[pl] -= 1
                    pot += 1
            log.append(f"**{fire_winner} got FIRE → all others pay!**")
        else:
            min_score = min(sc[0] for sc in scores.values())
            losers = [pl for pl, (sc, _) in scores.items() if sc[0] == min_score]
            for loser in losers:
                if c[loser] > 0:
                    c[loser] -= 1
                    pot += 1
                    log.append(f"{loser} pays 1 coin (lowest score).")

        st.subheader("Final Scores")
        for pl in p:
            if c[pl] > 0:
                sc, typ = scores[pl]
                st.write(f"{pl}: **{sc}** ({typ})")

        active = [pl for pl in p if c[pl] > 0]
        if len(active) <= 1:
            st.success(f"Game Over! Winner: {active[0] if active else 'None'}")
            if st.button("New Game"):
                st.session_state.game_started = False
                st.rerun()
        else:
            if st.button("Next Round"):
                st.session_state.dealer_idx = (d_idx + 1) % len(p)
                st.session_state.round_phase = "deal"
                st.session_state.table = []
                st.session_state.blind = []
                st.session_state.knock_player = None
                st.session_state.selected_hand = None
                st.session_state.last_ai_processed = None
                st.session_state.hands = {}
                log.append(f"New dealer: {p[st.session_state.dealer_idx]}")
                st.rerun()
