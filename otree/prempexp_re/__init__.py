from otree.api import *
import yaml
import random


doc = """
協力率を下げるためのパイロット実験
csv等から利得行列を読み込める仕組み必須
原型は以前演習で作ったものを利用。
"""

with open('otree/prempexp_re/test.yaml') as f: # 果たしてこんなところでyamlを読み込んで大丈夫なんでしょうか大丈夫でした
    payoff_matrix = yaml.safe_load(f)

class C(BaseConstants):
    NAME_IN_URL = 'prempexp'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 10
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

    def set_payoffs(self):
        p1, p2 = self.get_players()

        key1 = "round{}"
        key2 = "({}, {})"

        payoffs = C.PAYOFF_MATRIX[key1.format(self.continue_round)][key2.format(p1.decision_pd, p2.decision_pd)] # 継続ラウンドに応じて取り出す必要がある 入れ子の辞書が有力そう
        p1.payoff = payoffs[0]
        p2.payoff = payoffs[1]

    def set_continuation(self):
        p1, p2 = self.get_players()

        if p1.decision_continue == False or p2.decision_continue == False:
            self.end_game = True
        if self.max_round == self.continue_round:
            self.end_game = True

        if self.end_game == False:
            self.continue_round += 1
            p1.player_continue_round = self.continue_round
            p2.player_continue_round = self.continue_round
            






class Player(BasePlayer):
    decision_pd = models.BooleanField(
        label="あなたの行動を選択してください",
        choices=[[True, 'C'], [False, 'D']],
        widget=widgets.RadioSelect,
        doc='True: 協力, False: 非協力',
    )

    decision_continue = models.BooleanField(
        label="あなたは今の相手と次のラウンドも関係を続けますか",
        choices=[[True, 'はい'], [False, 'いいえ']],
        widget=widgets.RadioSelect,
        doc='True: 続ける, False: 続けない',
    )

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

class Matching(Page):
    pass # 今から新しい相手とやりとりが始まりますぜ的なアナウンスを入れるページ

class Interaction(Page):
    # @staticmethod
    # def vars_for_template(group: Group):
    #     pm = C.PAYOFF_MATRIX #TODO
    #     return
    
    # playerクラスのform_fieldを呼び出し
    form_model = 'player'
    form_fields = ['decision_pd']


class InteractionWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        group.set_payoffs()

class InteractionResult(Page):
    @staticmethod
    def vars_for_template(player: Player):
        opponent = player.get_others_in_group()[0]
        return {
            'player_decision': '協力' if player.decision_pd else '非協力',
            'opponent_decision': '非協力' if opponent.decision_pd else '非協力',
            'payoff': player.payoff,
        }


class BreakUp(Page):
    form_model = 'player'
    form_fields = ['decision_continue']

class BreakUpWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        group.set_continuation()

class BreakUpResult(Page):
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        return {'breakupresult': group.end_game}


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
    Matching,
    Interaction,
    InteractionWaitPage,
    InteractionResult,
    BreakUp,
    BreakUpWaitPage,
    BreakUpResult,
    FinalResults,
]
