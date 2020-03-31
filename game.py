import random
import hashlib

import words


NUM_LIBERAL_POLICIES = 6
NUM_FASCIST_POLICIES = 11
NUM_FASCISTS = 1

LIBERAL = "liberal"
FASCIST = "fascist"
HITLER = "hitler"


class Game:
    def __init__(self, seed, num_players, player_index, history=None):
        self.seed = seed
        self.num_players = num_players
        self.player_index = player_index

        random.seed(seed)
        self._set_role(num_players, player_index)

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

    def _set_role(self, num_players, player_index):
        num_liberals = num_players - NUM_FASCISTS - 1
        roles = [LIBERAL] * num_liberals + [FASCIST] * NUM_FASCISTS + [HITLER]
        random.shuffle(roles)
        self.role = roles[player_index]

    def _shuffle_deck(self):
        policies = [LIBERAL] * NUM_LIBERAL_POLICIES + [FASCIST] * NUM_FASCIST_POLICIES
        for policy in self.policy_mapping.values():
            policies.remove(policy)
        random.shuffle(policies)
        random.shuffle(self.discarded)
        for index, policy in zip(self.discarded, policies):
            self.policy_mapping[index] = policy

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
        return self.role

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

    # State transitions that can be taken during the game.
    def enact(self, policy):
        policies = self.deck[:3]
        index = -1
        for i, policy_index in enumerate(policies):
            if self.policy_mapping[policy_index] == policy:
                index = i
        assert index != -1, "Cannot enact a policy that wasn't in the top 3 cards. Try 'undo'?"

        for policy_index in policies:
            self.policy_mapping.pop(policy_index)
        policies.pop(index)

        if policy == LIBERAL:
            self.num_enacted_liberals += 1
        else:
            self.num_enacted_fascists += 1

        self.deck = self.deck[3:]
        self.discarded += policies
        if len(self.deck) < 3:
            self._shuffle_deck()
        self.log.append(("enact", (policy, )))
        return "\n".join([self.get_enacted_policies(), self._checksum()])

    def reveal(self):
        policy_index = self.deck.pop(0)
        policy = self.policy_mapping.pop(policy_index)

        if policy == LIBERAL:
            self.num_enacted_liberals += 1
        else:
            self.num_enacted_fascists += 1

        self.discarded.append(policy_index)
        if len(self.deck) < 3:
            self._shuffle_deck()
        self.log.append(("reveal", ()))
        return "\n".join([self.get_enacted_policies(), self._checksum()])

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
    # Actions that affect game state.
    "enact": (Game.enact, "Enact a policy"),
    "reveal": (Game.reveal, "Enact the policy at the top of the deck"),
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
    game = Game(seed, num_players, player_index)
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
    main(args.seed, args.num_players, args.player_index - 1)
