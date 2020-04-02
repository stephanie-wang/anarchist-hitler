import random
import hashlib
import sys

import words


NUM_LIBERAL_POLICIES = 6
NUM_FASCIST_POLICIES = 11
NUM_FASCISTS = {
    5: 1,
    6: 1,
    7: 2,
    8: 2,
    9: 3,
    10: 3,
}

LIBERAL = "liberal"
FASCIST = "fascist"
HITLER = "hitler"


class Game:
    def __init__(self, seed, num_players, player_index, history=None):
        assert num_players >= min(NUM_FASCISTS), "Minimum number of players is 5"
        assert num_players <= max(NUM_FASCISTS), "Maximum number of players is 10"
        assert player_index >= 1 and player_index <= num_players, "Player index must be between 1 and the total number of players"

        self.seed = seed
        self.num_players = num_players
        self.player_index = player_index

        random.seed(seed)
        self._set_roles(num_players)

        self.discarded = list(range(NUM_LIBERAL_POLICIES + NUM_FASCIST_POLICIES))
        self.policy_mapping = {}
        self.deck = []
        self._shuffle_deck()

        self.num_enacted_liberals = 0
        self.num_enacted_fascists = 0
        self.log = []
        history = history or []
        for policy, args in history:
            method = getattr(Game, policy)
            method(self, *args)

    def _set_roles(self, num_players):
        num_fascists = NUM_FASCISTS[num_players]
        num_liberals = num_players - num_fascists - 1
        self.roles = [(LIBERAL, LIBERAL)] * num_liberals + [(FASCIST, FASCIST)] * num_fascists + [(FASCIST, HITLER)]
        random.shuffle(self.roles)

    def _shuffle_deck(self):
        # Shuffle the remaining cards in the deck into the discarded pile.
        while self.deck:
            index = self.deck.pop(0)
            self.discarded.append(index)
            self.policy_mapping.pop(index)
        assert len(self.policy_mapping) == 0, self.policy_mapping

        # Generate a random permutation from index to policy.
        policies = [LIBERAL] * NUM_LIBERAL_POLICIES + [FASCIST] * NUM_FASCIST_POLICIES
        random.shuffle(policies)
        for index, policy in zip(self.discarded, policies):
            self.policy_mapping[index] = policy
        # Shuffle the deck.
        random.shuffle(self.discarded)
        while self.discarded:
            self.deck.append(self.discarded.pop(0))

    def _checksum(self):
        m = hashlib.md5()
        m.update(str(self.seed).encode('ascii'))
        for index in self.deck:
            m.update(str(index).encode('ascii'))
            m.update(str(self.policy_mapping[index]).encode('ascii'))
        for index in self.discarded:
            m.update(str(index).encode('ascii'))
        checksum = int(m.hexdigest(), 16)
        return "Checksum: {}".format(words.WORDS[checksum % len(words.WORDS)])

    # Read-only actions that can be taken during the game.
    def get_role(self):
        # Zero-index the players.
        return "{} : {}".format(self.player_index, self.roles[self.player_index - 1])

    def investigate(self, player_index):
        player_index = int(player_index)
        assert player_index != self.player_index, "You cannot investigate yourself"
        assert player_index >= 1 and player_index <= self.num_players, "Player index must be between 1 and the total number of players"
        # Zero-index the players.
        return "{} : {}".format(player_index, self.roles[player_index - 1][0])

    def look(self, *indices):
        policies = []
        for index in indices:
            index = int(index)
            assert index in self.deck[:3], "Tried to look at a card that wasn't drawn"
            policies.append(self.policy_mapping[index])
        return ", ".join(policies)

    def draw(self):
        return "\n".join("{} {}".format(index, self.policy_mapping[index]) for index in self.deck[:3])

    def get_enacted_policies(self):
        return "Liberal policies: {}, Fascist policies: {}".format(self.num_enacted_liberals, self.num_enacted_fascists)

    def _enact(self, discarded, index_to_enact=None):
        # Enact the policy.
        if index_to_enact is not None:
            policy = self.policy_mapping[index_to_enact]
            if policy == LIBERAL:
                self.num_enacted_liberals += 1
            else:
                self.num_enacted_fascists += 1

        # Discard the remaining cards without revealing them.
        for policy_index in discarded:
            self.deck.pop(0)
            self.policy_mapping.pop(policy_index)
        if index_to_enact is not None:
            self.deck.pop(0)
            policy = self.policy_mapping.pop(index_to_enact)
        self.discarded += discarded
        if len(self.deck) < 3:
            self._shuffle_deck()

        return "\n".join([self.get_enacted_policies(), self._checksum()])

    # State transitions that can be taken during the game.
    def enact(self, policy):
        policies = self.deck[:3]
        index = -1
        for i, policy_index in enumerate(policies):
            if self.policy_mapping[policy_index] == policy:
                index = i
        assert index != -1, "Cannot enact a policy that wasn't in the top 3 cards. Try 'undo'?"
        policy_index = policies.pop(index)
        self.log.append(("enact", (policy, )))
        return self._enact(policies, index_to_enact=policy_index)

    def reveal(self):
        self.log.append(("reveal", ()))
        return self._enact([], index_to_enact=self.deck[0])

    def veto(self):
        self.log.append(("veto", ()))
        return self._enact(self.deck[:3])

    def undo(self):
        assert len(self.log) > 0, "No actions to undo"
        log = self.log[:]
        log.pop(-1)
        self.__init__(self.seed, self.num_players, self.player_index, log)
        return self._checksum()


ACTIONS = {
    # Read-only actions.
    "role": (Game.get_role, "Get your role"),
    "draw": (Game.draw, "Look at the top 3 cards of the deck"),
    "look": (Game.look, "Look at the value of the given card(s). This can be any one of the top 3 cards. Example: look 8 10"),
    "check": (Game.get_enacted_policies, "Check which policies have been enacted so far"),
    "investigate": (Game.investigate, "Check one other player's party membership"),
    # Actions that affect game state.
    "enact": (Game.enact, "Enact a policy"),
    "reveal": (Game.reveal, "Enact the policy at the top of the deck"),
    "veto": (Game.veto, "Veto the current legislation"),
    "undo": (Game.undo, "Undo the last action played"),
}


def execute_command(game, raw_command):
    command = raw_command.split()
    assert len(command) >= 1
    action = command.pop(0)
    assert action in ACTIONS, "Invalid action"
    try:
        return ACTIONS[action][0](game, *command)
    except TypeError:
        print("Wrong arguments. Try 'help'?")


def main(seed, num_players, player_index):
    try:
        game = Game(seed, num_players, player_index)
    except AssertionError as e:
        print(e)
        sys.exit()
    print("Starting", game._checksum())
    while True:
        command = input(">> ")
        command = command.lower().strip()
        if command == "help":
            for name, method in ACTIONS.items():
                description = method[1]
                print(name, ":", description)
            continue
        elif command == "quit" or command == "q":
            break
        else:
            try:
                val = execute_command(game, command)
                if val:
                    print(val)
            except AssertionError as e:
                print(e)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument("--seed", required=True, type=int,
            help="Seed for the random number generator. This must be the same for all players.")
    parser.add_argument("--num-players", required=True, type=int,
            help="The total number of players. This must be the same for all players.")
    parser.add_argument("--player-index", required=True, type=int,
            help="Your player index. This must be unique for each player and should be a number between 1 and the total number of players.")

    args = parser.parse_args()
    main(args.seed, args.num_players, args.player_index)
