from otree.api import *
import yaml
import random


doc = """
協力率を下げるためのパイロット実験
csv等から利得行列を読み込める仕組み必須
原型は以前演習で作ったものを利用。
"""

with open('otree/prempexp_livepage_re/test.yaml') as f: # 果たしてこんなところでyamlを読み込んで大丈夫なんでしょうか大丈夫でした
    payoff_matrix = yaml.safe_load(f)

class C(BaseConstants):
    NAME_IN_URL = 'prempexp_livepage'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 3
    PAYOFF_MATRIX = payoff_matrix 
    CONTINUATION_PROB = [0, 0, 0, 0.1, 0.15, 0.25, 0.25, 0.15, 0.1, 0, 0, 0]


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    max_round = models.IntegerField(initial=1)
    continue_round = models.IntegerField(initial=1)
    end_game = models.BooleanField(initial=False)

    def set_max_round(self):
        self.max_round = random.choices(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], 
            weights=C.CONTINUATION_PROB, 
            k=1)[0] #恣意的に定めた確率分布から、ペアが継続する回数をペア成立時に決定
        



    # def set_payoffs(self):
    #     p1, p2 = self.get_players()

    #     key1 = "round{}"
    #     key2 = "({}, {})"

    #     payoffs = C.PAYOFF_MATRIX[key1.format(self.continue_round)][key2.format(p1.decision_pd, p2.decision_pd)] # 継続ラウンドに応じて取り出す必要がある 入れ子の辞書が有力そう
    #     p1.payoff = payoffs[0]
    #     p2.payoff = payoffs[1]

    # def set_continuation(self):
    #     p1, p2 = self.get_players()

    #     if p1.decision_continue == False or p2.decision_continue == False:
    #         self.end_game = True
    #     if self.max_round == self.continue_round:
    #         self.end_game = True

    #     if self.end_game == False:
    #         self.continue_round += 1
    #         p1.player_continue_round = self.continue_round
    #         p2.player_continue_round = self.continue_round

            

def set_payoffs(group):
    p1, p2 = group.get_players()
    continue_round = group.continue_round

    key1 = "round{}"
    key2 = "({}, {})"

    payoffs = C.PAYOFF_MATRIX[key1.format(continue_round)][key2.format(bool(p1.decision_pd), bool(p2.decision_pd))] # 継続ラウンドに応じて取り出す必要がある 入れ子の辞書が有力そう
    p1.payoff = payoffs[0]
    p2.payoff = payoffs[1]

def set_continuation(group):
    p1, p2 = group.get_players()
    p1_decision_continue = bool(p1.field_maybe_none('decision_continue'))
    p2_decision_continue = bool(p2.field_maybe_none('decision_continue'))

    if p1_decision_continue == False or p2_decision_continue == False:
        group.end_game = True
    if group.max_round == group.continue_round:
        group.end_game = True

    if group.end_game == False:
        group.continue_round += 1
        p1.player_continue_round = group.continue_round
        p2.player_continue_round = group.continue_round


class Player(BasePlayer):
    decision_pd = models.BooleanField()

    opponent_decision_pd = models.BooleanField()

    decision_continue = models.BooleanField()

    is_rematched = models.BooleanField(initial=True)
    player_max_round = models.IntegerField(initial=1)
    player_continue_round = models.IntegerField(initial=1)

    def get_cumulative_payoff(self):
        return sum([p.payoff for p in self.in_all_rounds() if p.payoff is not None])
    


def matchingsort(subsession: Subsession):

    if subsession.round_number == 1:
        subsession.group_randomly()
        for g in subsession.get_groups():
            g.set_max_round()
            g.get_players()[0].player_max_round = g.max_round
            g.get_players()[1].player_max_round = g.max_round
        for p in subsession.get_players():
        #     current_group = subsession.get_groups()
            p.is_rematched = True
        #     p.max_round_p = current_group.max_round

    else:
        prev_groups = subsession.in_round(subsession.round_number - 1).get_groups()
        continued_groups = []
        rematch_pool = []

        for g in prev_groups:
            if g.end_game == False:
                current_round_players = [_.in_round(subsession.round_number) for _ in g.get_players()]
                continued_groups.append(current_round_players)
                for p in current_round_players:
                    p.is_rematched = False
                    p.player_max_round = p.in_round(subsession.round_number - 1).player_max_round
                    p.player_continue_round = p.in_round(subsession.round_number - 1).player_continue_round
            else:
                current_round_players = [_.in_round(subsession.round_number) for _ in g.get_players()]
                rematch_pool.extend(current_round_players)
                for p in current_round_players:
                    p.is_rematched = True
        random.shuffle(rematch_pool)
        new_groups_matrix = [rematch_pool[i:i+2] for i in range(0, len(rematch_pool), 2)]

        final_matrix = continued_groups + new_groups_matrix

        subsession.set_group_matrix(final_matrix)

        for g in subsession.get_groups():
            g.set_max_round()
            sample = g.get_players()[0] 
            if sample.is_rematched == False:
                g.max_round = sample.player_max_round
                g.continue_round = sample.player_continue_round
            else:
                g.get_players()[0].player_max_round = g.max_round
                g.get_players()[1].player_max_round = g.max_round




def live_method(player: Player, data):
        group = player.group
        players = group.get_players()
        p1, p2 = players
        # 先に送ってきたやつに「少々お待ちください」を表示させたい,これはjava側で実装可能でした
        if data:
            print("data", data)
            choice = data['decision_pd']
            # print(choice)
            player.decision_pd = choice
            # print(player.decision_pd)
            # print(p1, p2)
            # print(p1.field_maybe_none("decision_pd"))

            if p1.field_maybe_none("decision_pd") != None and p2.field_maybe_none("decision_pd") != None:

                set_payoffs(group) # なんだここ！いやまあいけるか
                p1.opponent_decision_pd = p2.decision_pd
                p2.opponent_decision_pd = p1.decision_pd
            
                return {
                    p.id_in_group: dict(
                        payoff = p.payoff,
                        player_decision = p.field_maybe_none("decision_pd"),
                        opponent_decision = p.field_maybe_none("opponent_decision_pd"),
                    )
                    for p in players
                }
        
    

# PAGES
class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class MatchingWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession: Subsession): # wait_for_all_groups = Trueなので、サブセッションの関数としてオーバーライド
        matchingsort(subsession)



class Match_Interaction(Page):
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        continue_round = group.continue_round
        key1 = "round{}"
        current_payoff_matrix = C.PAYOFF_MATRIX[key1.format(continue_round)]
        return {
            'payoff_CC': current_payoff_matrix['(True, True)'],
            'payoff_CD': current_payoff_matrix['(True, False)'],
            'payoff_DC': current_payoff_matrix['(False, True)'],
            'payoff_DD': current_payoff_matrix['(False, False)'],
        }
    
    live_method = live_method

    
    

class BreakUp(Page):
    @staticmethod
    def live_method(player: Player, data):
        group = player.group
        players = group.get_players()
        p1, p2 = players

        if data:
            print("data", data)
            choice = data['decision_continue']
            player.decision_continue = choice

            if p1.field_maybe_none('decision_continue') != None and p2.field_maybe_none('decision_continue') != None:
                    set_continuation(group)
                    return {
                        0: dict(
                            end_game = group.end_game)}





class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS
    
    @staticmethod
    def vars_for_template(player: Player):
        return {'cumulative_payoff': player.get_cumulative_payoff()}


page_sequence = [
    Introduction, 
    MatchingWaitPage,
    Match_Interaction,
    BreakUp,
    FinalResults,
]
