# SimplePokerSolver
A simple but limited poker solver that doesn't take too much RAM; uilizes sample ranges in GTO solver

Summary of How the Program Works, Its Assumptions, and Its Potential Uses:

How It Works:

Inputs & Setup:
The program uses a graphical user interface (GUI) built with Tkinter. The user inputs key variables: the player's hand, the current board (if any), both players' stack sizes, the opponent's bet size (in big blinds), and the pot size.


Below are assumption of this poker "solver" operates upon

Opponent Range & Simulation:

The opponent’s range is loaded from a text file (assumed to be accurate). Using this range, the program simulates many possible board runouts (via Monte Carlo simulation) with the help of the Treys library to evaluate hand strengths.

Dynamic Folding Rules:

It applies a series of custom folding rules to approximate how an opponent might fold their calling range based on factors like:

If the opponent’s hand makes two pair (as determined by the evaluator’s rank class 8) and the board itself is unpaired, the opponent never folds.

If the opponent’s two cards are of the same suit and the board contains at least three cards of that suit, the opponent is considered to have a made flush.

In particular, if the flush includes an Ace, the opponent never folds.

If the opponent’s hole cards are both suited and connected (which indicates strong draw potential), they never fold.

If the opponent doesn’t have a pair, top pair, or overpair—and has no draw potential—they fold if the bet is at least 25% of the pot.
Top Pair or Overpair:

If the opponent has top pair or an overpair (a pocket pair higher than the board’s highest card), they will not fold to bets up to 1.5×pot.
They will fold only if the bet exceeds 1.5×pot.
Suited or Connected (but Not Both):

If the opponent’s cards are either suited or connected (but not both), they fold to bets of at least 1.5×pot.

If the opponent holds a pocket pair that is lower than the board’s highest card, they fold to bets of 0.8×pot or more—but only if they do not have a set (i.e. if neither hole card appears on the board).
If they do have a set, they normally do not fold—unless the board is monotone (all cards of the same suit) with exactly 4 cards, in which case even a set will fold only if the bet reaches the “all‑in” threshold.

If the opponent has a full house (or better) or even two pair, they never fold—unless (in a very simplified manner) neither of their hole cards contributes to the best five‐card hand (interpreted as having “no value”).
Default:

If none of these rules force a fold, the opponent does not fold.

These Rules are adjustable in the source code, and in the future will be togglable in the GUI

EV Calculation:

The program computes the expected value (EV) for different actions. It distinguishes between two branches:

When the opponent bets (>0): Options include folding, calling, or betting with several bet sizes (minimum bet is double the opponent’s bet, half-pot, full pot, and all-in).

When the opponent checks (bet = 0): The options are to check or to bet with sizes like small (¼ pot), large (0.8×pot), overbet (1.5×pot), and all-in.

For each candidate bet, a “dynamic fold probability” is computed—restricting the opponent’s calling range—and then used to derive the EV.

Output:
Finally, the program displays the estimated win rate along with the EVs for each action, recommending the best overall action based on the simulation results.
