import os
import random
import itertools
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from treys import Card, Evaluator

def parse_opponent_range(range_str):
    items = range_str.split(',')
    distribution = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        if ':' in item:
            designation, freq_str = item.split(':')
            freq = float(freq_str)
        else:
            designation = item
            freq = 1.0
        designation = designation.strip()
        if len(designation) == 2:
            base = 12 if designation[0] == designation[1] else 16
        elif len(designation) == 3:
            if designation[2].lower() == 's':
                base = 4
            elif designation[2].lower() == 'o':
                base = 12
            else:
                base = 16
        else:
            base = 16
        distribution.append((designation, freq * base))
    return distribution

def hand_matches_combo(designation, card1, card2):
    cs1 = Card.int_to_str(card1)
    cs2 = Card.int_to_str(card2)
    rank1, suit1 = cs1[0], cs1[1]
    rank2, suit2 = cs2[0], cs2[1]
    des = designation.strip().upper()
    if len(des) == 2:
        if des[0] == des[1]:
            return rank1 == des[0] and rank2 == des[0]
        else:
            return {rank1, rank2} == {des[0], des[1]}
    elif len(des) == 3:
        r1, r2, typ = des[0], des[1], des[2]
        if {rank1, rank2} != {r1, r2}:
            return False
        if typ == 'S':
            return suit1 == suit2
        elif typ == 'O':
            return suit1 != suit2
    return False

def get_random_hand_combo(designation, removed_cards):
    available_cards = [card for card in create_standard_deck() if card not in removed_cards]
    valid_combos = []
    for combo in itertools.combinations(available_cards, 2):
        if hand_matches_combo(designation, combo[0], combo[1]):
            valid_combos.append(combo)
    return random.choice(valid_combos) if valid_combos else None

def create_standard_deck():
    ranks = "23456789TJQKA"
    suits = "shdc"
    return [Card.new(rank + suit) for rank in ranks for suit in suits]

def best_response_win_rate_range(hero_hand, opponent_range_str, known_board, iterations=1000):
    evaluator = Evaluator()
    hero_cards = [Card.new(card) for card in hero_hand]
    board_cards = [Card.new(card) for card in known_board]
    num_to_deal = 5 - len(board_cards)
    opp_distribution = parse_opponent_range(opponent_range_str)
    designations = [d for d, w in opp_distribution]
    weights = [w for d, w in opp_distribution]
    simulation_win = 0.0
    simulation_count = 0
    for _ in range(iterations):
        removed = set(hero_cards + board_cards)
        designation = random.choices(designations, weights=weights, k=1)[0]
        opp_combo = get_random_hand_combo(designation, removed)
        if opp_combo is None:
            continue
        removed_extended = removed.union(set(opp_combo))
        deck_remaining = [card for card in create_standard_deck() if card not in removed_extended]
        if num_to_deal > 0:
            if len(deck_remaining) < num_to_deal:
                continue
            simulated_board = board_cards.copy()
            simulated_board.extend(random.sample(deck_remaining, num_to_deal))
        else:
            simulated_board = board_cards.copy()
        hero_rank = evaluator.evaluate(hero_cards, simulated_board)
        opp_rank = evaluator.evaluate(list(opp_combo), simulated_board)
        if hero_rank < opp_rank:
            simulation_win += 1
        elif hero_rank == opp_rank:
            simulation_win += 0.5
        simulation_count += 1
    if simulation_count == 0:
        return 0
    return simulation_win / simulation_count

# Updated opponent fold decision with additional rules.
# New parameter all_in_bet (default None) indicates the bet amount considered "all in".
def opponent_fold_decision(opp_hand, board, bet_size, pot, all_in_bet=None):
    order = "23456789TJQKA"
    evaluator = Evaluator()
    board_ranks = [card[0] for card in board]
    board_is_paired = any(board_ranks.count(r) >= 2 for r in board_ranks) if board else False
    # Full house evaluation:
    opp_value = evaluator.evaluate([Card.new(opp_hand[0]), Card.new(opp_hand[1])],
                                    [Card.new(card) for card in board]) if board else None
    opp_class = evaluator.get_rank_class(opp_value) if opp_value else None
    # Rule: 2 pair hands never fold if board is unpaired.
    if not board_is_paired and opp_class == 8:
        return False
    # Rule: Made flushes never fold.
    opp_suits = [opp_hand[0][1], opp_hand[1][1]]
    if board:
        board_suits = [card[1] for card in board]
        if opp_suits[0] == opp_suits[1] and board_suits.count(opp_suits[0]) >= 3:
            # If flush with an Ace, never fold.
            if 'A' in [opp_hand[0][0], opp_hand[1][0]]:
                return False
            return False
    is_pair = (opp_hand[0][0] == opp_hand[1][0])
    pair_rank = opp_hand[0][0] if is_pair else None
    board_high = max(board, key=lambda card: order.index(card[0]))[0] if board else None
    is_top_pair = False
    if board_high:
        is_top_pair = (opp_hand[0][0] == board_high or opp_hand[1][0] == board_high)
    is_overpair = False
    if is_pair and board_high:
        if order.index(pair_rank) > order.index(board_high):
            is_overpair = True
    is_suited = (opp_hand[0][1] == opp_hand[1][1])
    idx0 = order.index(opp_hand[0][0])
    idx1 = order.index(opp_hand[1][0])
    is_connected = abs(idx0 - idx1) <= 2
    # Rule: Suited and connected hands never fold.
    if is_suited and is_connected:
        return False
    # Rule 1: No pair and no draw => fold if bet >= 0.25*pot.
    has_draw = is_suited and is_connected  # if both, draw is strong; already covered above.
    if (not is_pair) and (not is_top_pair) and (not is_overpair) and (not has_draw):
        if bet_size >= 0.25 * pot:
            return True
    # Rule 2: Top pair or overpair do not fold to bets up to 1.5×pot; only fold if bet > 1.5×pot.
    if is_top_pair or is_overpair:
        if bet_size > 1.5 * pot:
            return True
        else:
            return False
    # Rule 3: Suited OR connected (but not both) fold to bets >= 1.5×pot.
    if (is_suited or is_connected) and not (is_suited and is_connected):
        if bet_size >= 1.5 * pot:
            return True
    # Rule 4: For a pocket pair, check for a set.
    if is_pair and board_high:
        is_set = (opp_hand[0][0] in board_ranks or opp_hand[1][0] in board_ranks)
        if order.index(pair_rank) < order.index(board_high):
            if not is_set:
                if bet_size >= 0.8 * pot:
                    return True
            else:
                # If they have a set, they never fold—unless the board is monotone with exactly 4 cards.
                board_suits = [card[1] for card in board]
                board_monotone = (len(set(board_suits)) == 1 and len(board) == 4)
                if board_monotone:
                    # Now, if an all_in bet is being offered (all_in_bet is provided) and bet_size is at least that, they fold.
                    if bet_size >= 1.6 * pot:
                        return True
                    else:
                        return False
    # Rule 5: Full house or better (two pair or more) never fold unless hole cards contribute nothing.
    if opp_class is not None and opp_class <= 7:
        if (opp_hand[0][0] not in board_ranks and opp_hand[1][0] not in board_ranks):
            return True
    return False

# Updated calculate_dynamic_fold_probability to pass along all_in_bet.
def calculate_dynamic_fold_probability(hero_hand, opponent_range_str, board, total_bet, pot, iterations=500, all_in_bet=None):
    fold_count = 0
    count = 0
    hero_cards = [Card.new(card) for card in hero_hand]
    for _ in range(iterations):
        removed = set(hero_cards + [Card.new(card) for card in board])
        opp_dist = parse_opponent_range(opponent_range_str)
        designations = [d for d, w in opp_dist]
        weights = [w for d, w in opp_dist]
        designation = random.choices(designations, weights=weights, k=1)[0]
        opp_combo = get_random_hand_combo(designation, removed)
        if opp_combo is None:
            continue
        opp_hand = [Card.int_to_str(card) for card in opp_combo]
        if opponent_fold_decision(opp_hand, board, total_bet, pot, all_in_bet):
            fold_count += 1
        count += 1
    return fold_count / count if count > 0 else 0

def evaluate_actions(hero_hand, opponent_range_str, board, pot, opp_bet, hero_stack, opp_stack, iterations=1000):
    if opp_bet > 0:
        call_cost = opp_bet
        win_rate = best_response_win_rate_range(hero_hand, opponent_range_str, board, iterations)
        EV_fold = 0
        EV_call = win_rate * pot - (1 - win_rate) * call_cost
        candidate_options = {
            "min raise": min(2 * opp_bet, hero_stack, opp_stack),
            "half_pot raise": min((pot + 2*opp_bet) / 2 + opp_bet, hero_stack, opp_stack),
            "pot raise": min((pot + 2*opp_bet) + opp_bet, hero_stack, opp_stack)
        }
        all_in_candidate = min(hero_stack, opp_stack) - call_cost
        if all_in_candidate > 0:
            candidate_options["all_in"] = all_in_candidate
        bet_options = {}
        for option, candidate in candidate_options.items():
            total_commitment = call_cost + candidate
            # For the "all_in" candidate, pass candidate as all_in_bet; otherwise, None.
            current_all_in = candidate if option == "all_in" else None
            call_rate = 1 - calculate_dynamic_fold_probability(hero_hand, opponent_range_str, board, total_commitment, pot, iterations=500, all_in_bet=current_all_in)
            EV_raise_if_called = call_rate * (pot + total_commitment) - (1 - call_rate) * total_commitment
            EV_raise = (1 - call_rate) * (pot - total_commitment) + call_rate * EV_raise_if_called
            bet_options[option] = {"bet_amount": candidate, "EV": EV_raise}
        best_bet = None
        if bet_options:
            best_bet_option = max(bet_options, key=lambda k: bet_options[k]["EV"])
            best_bet = bet_options[best_bet_option].copy()
            best_bet["option"] = best_bet_option
        best_overall = "fold"
        best_overall_EV = EV_fold
        if EV_call > best_overall_EV:
            best_overall = "call"
            best_overall_EV = EV_call
        if best_bet is not None and best_bet["EV"] > best_overall_EV:
            best_overall = f"bet ({best_bet['option']})"
            best_overall_EV = best_bet["EV"]
        return {
            "win_rate": win_rate,
            "fold": EV_fold,
            "call": EV_call,
            "bet_options": bet_options,
            "best_bet": best_bet,
            "best_overall": best_overall,
            "best_overall_EV": best_overall_EV
        }
    else:
        win_rate = best_response_win_rate_range(hero_hand, opponent_range_str, board, iterations)
        EV_check = win_rate * pot
        candidate_options = {
            "small": 0.25 * pot,
            "large": 0.8 * pot,
            "overbet": 1.5 * pot,
            "all_in": min(hero_stack, opp_stack)
        }
        bet_options = {}
        for option, candidate in candidate_options.items():
            total_bet = candidate
            current_all_in = candidate if option == "all_in" else None
            call_rate = 1 - calculate_dynamic_fold_probability(hero_hand, opponent_range_str, board, total_bet, pot, iterations=500, all_in_bet=current_all_in)
            EV_bet = call_rate * (pot + candidate) - (1 - call_rate) * candidate
            bet_options[option] = {"bet_amount": candidate, "EV": EV_bet}
        best_bet = None
        if bet_options:
            best_bet_option = max(bet_options, key=lambda k: bet_options[k]["EV"])
            best_bet = bet_options[best_bet_option].copy()
            best_bet["option"] = best_bet_option
        best_overall = "check"
        best_overall_EV = EV_check
        if best_bet is not None and best_bet["EV"] > best_overall_EV:
            best_overall = f"bet ({best_bet['option']})"
            best_overall_EV = best_bet["EV"]
        return {
            "win_rate": win_rate,
            "check": EV_check,
            "bet_options": bet_options,
            "best_bet": best_bet,
            "best_overall": best_overall,
            "best_overall_EV": best_overall_EV
        }

def parse_cards(card_str):
    card_str = card_str.strip()
    return [card_str[i:i+2] for i in range(0, len(card_str), 2)]

class PokerEVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker EV Calculator")
        self.root.geometry("500x700")
        self.root.bind("<Escape>", lambda e: self.root.quit())
        self.last_enter_time = 0
        self.opponent_range_str = ""
        self.range_file_path = ""
        self.select_range_file()
        self.create_widgets()
        self.root.bind("<Return>", self.on_enter_key)

    def select_range_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Opponent Range File",
            initialdir=os.getcwd(),
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not file_path:
            messagebox.showerror("Error", "No range file selected. Exiting.")
            self.root.quit()
        else:
            self.range_file_path = file_path
            with open(file_path, "r") as f:
                self.opponent_range_str = f.read()

    def create_widgets(self):
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=10)
        tk.Label(input_frame, text=f"Range File: {os.path.basename(self.range_file_path)}").grid(row=0, column=0, columnspan=2, pady=5)
        tk.Label(input_frame, text="Player's Hand (e.g., AhQs):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.hero_hand_entry = tk.Entry(input_frame, width=20)
        self.hero_hand_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(input_frame, text="Board (e.g., 7s8s9s or leave blank):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.board_entry = tk.Entry(input_frame, width=20)
        self.board_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(input_frame, text="Player's Stack (e.g., 56.5):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.hero_stack_entry = tk.Entry(input_frame, width=20)
        self.hero_stack_entry.grid(row=3, column=1, padx=5, pady=5)
        tk.Label(input_frame, text="Opponent's Stack (e.g., 66.2):").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.opp_stack_entry = tk.Entry(input_frame, width=20)
        self.opp_stack_entry.grid(row=4, column=1, padx=5, pady=5)
        tk.Label(input_frame, text="Opponent's Bet (in bb, e.g., 10 or 0):").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        self.opp_bet_entry = tk.Entry(input_frame, width=20)
        self.opp_bet_entry.grid(row=5, column=1, padx=5, pady=5)
        tk.Label(input_frame, text="Pot Size (in bb, e.g., 100):").grid(row=6, column=0, sticky="e", padx=5, pady=5)
        self.pot_entry = tk.Entry(input_frame, width=20)
        self.pot_entry.grid(row=6, column=1, padx=5, pady=5)
        self.calc_button = tk.Button(self.root, text="Calculate EV", command=self.calculate_ev)
        self.calc_button.pack(pady=10)
        self.output_text = tk.Text(self.root, height=10, width=60)
        self.output_text.pack(pady=10)
        self.output_text.config(state=tk.DISABLED)
        tk.Label(self.root, text="Press Enter twice quickly to reset for another hand. Press Esc to quit.").pack(pady=5)

    def calculate_ev(self):
        hero_hand_str = self.hero_hand_entry.get().strip()
        board_str = self.board_entry.get().strip()
        hero_stack_str = self.hero_stack_entry.get().strip()
        opp_stack_str = self.opp_stack_entry.get().strip()
        opp_bet_str = self.opp_bet_entry.get().strip()
        pot_str = self.pot_entry.get().strip()
        if not hero_hand_str or not hero_stack_str or not opp_stack_str or opp_bet_str == "" or pot_str == "":
            messagebox.showerror("Error", "Please fill in player's hand, both stack sizes, opponent's bet, and pot size.")
            return
        try:
            hero_stack = float(hero_stack_str)
            opp_stack = float(opp_stack_str)
            opp_bet = float(opp_bet_str)
            pot = float(pot_str)
        except ValueError:
            messagebox.showerror("Error", "Stack sizes, opponent's bet, and pot size must be numbers.")
            return
        hero_hand = parse_cards(hero_hand_str)
        if len(hero_hand) != 2:
            messagebox.showerror("Error", "Player's hand must be exactly 2 cards (e.g., AhQs).")
            return
        board = parse_cards(board_str) if board_str else []
        if opp_bet > 0:
            results = evaluate_actions(hero_hand, self.opponent_range_str, board,
                                       pot, opp_bet, hero_stack, opp_stack, iterations=10000)
            out_str = f"Estimated Win Rate: {results['win_rate']:.3f}\n"
            out_str += f"EV (Fold): {results['fold']:.2f}\n"
            out_str += f"EV (Call): {results['call']:.2f}\n"
            out_str += "Bet Options:\n"
            for option, data in results["bet_options"].items():
                out_str += f"  {option}: Bet Amount = {data['bet_amount']:.2f}, EV = {data['EV']:.2f}\n"
            if results["best_bet"]:
                best_bet = results["best_bet"]
                out_str += f"Best Bet Option: {best_bet['option']} (Bet Amount = {best_bet['bet_amount']:.2f}, EV = {best_bet['EV']:.2f})\n"
            out_str += f"Overall Best Action: {results['best_overall']} with EV = {results['best_overall_EV']:.2f}\n"
        else:
            results = evaluate_actions(hero_hand, self.opponent_range_str, board,
                                       pot, opp_bet, hero_stack, opp_stack, iterations=10000)
            out_str = f"Estimated Win Rate: {results['win_rate']:.3f}\n"
            out_str += f"EV (Check): {results['check']:.2f}\n"
            out_str += "Bet Options:\n"
            for option, data in results["bet_options"].items():
                out_str += f"  {option}: Bet Amount = {data['bet_amount']:.2f}, EV = {data['EV']:.2f}\n"
            if results["best_bet"]:
                best_bet = results["best_bet"]
                out_str += f"Best Bet Option: {best_bet['option']} (Bet Amount = {best_bet['bet_amount']:.2f}, EV = {best_bet['EV']:.2f})\n"
            out_str += f"Overall Best Action: {results['best_overall']} with EV = {results['best_overall_EV']:.2f}\n"
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, out_str)
        self.output_text.config(state=tk.DISABLED)

    def on_enter_key(self, event):
        current_time = time.time()
        if current_time - self.last_enter_time < 1:
            self.reset_fields()
        self.last_enter_time = current_time

    def reset_fields(self):
        self.hero_hand_entry.delete(0, tk.END)
        self.board_entry.delete(0, tk.END)
        self.hero_stack_entry.delete(0, tk.END)
        self.opp_stack_entry.delete(0, tk.END)
        self.opp_bet_entry.delete(0, tk.END)
        self.pot_entry.delete(0, tk.END)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)

if __name__ == '__main__':
    root = tk.Tk()
    app = PokerEVApp(root)
    root.mainloop()
