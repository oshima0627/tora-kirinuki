"""分類が判定カードの文字列から一意に決まることを確かめる。"""

from scripts.sync_playlists import classify


def test_kanzen_all_is_seiritsu():
    assert classify("完全ALL成立") == "成立"
    assert classify("ALL成立 200万円") == "成立"
    assert classify("完全ALL（エクシード達成）") == "成立"
    assert classify("この区間の後、完全ALL成立（リベンジ達成）") == "成立"


def test_nothing_is_fuseiritsu():
    assert classify("ナッシング（不成立）") == "不成立"
    assert classify("ナッシング（200万円）") == "不成立"
    assert classify("この回の最終結果はナッシング（いいね4・ごめんなさい1）") == "不成立"


def test_kyouryoku_wins_over_nothing():
    # 「ごめんなさい0（協力確約）」はナッシングの語を含まないが、
    # 「ナッシング（いいね4・ごめんなさい1）」と紛らわしい。協力確約を先に見る
    assert classify("どっぷり手伝う3・ふんわり2・ごめんなさい0（協力確約）") == "協力確約"
    assert classify("どっぷり手伝う（協力確約）") == "協力確約"


def test_unknown_is_none():
    assert classify("") is None
    assert classify("この時点で100万円") is None
    assert classify("【要裏取り】判定") is None
