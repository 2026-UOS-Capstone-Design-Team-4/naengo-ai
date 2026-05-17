from app.agents.responders.smalltalk import SmalltalkResponder


def test_smalltalk_responder_varies_short_replies():
    responder = SmalltalkResponder()

    assert "안녕하세요" in responder.respond("ㅎㅇ")
    assert "천만에요" in responder.respond("고마워")
    assert "좋아요" in responder.respond("ㅇㅋ")
    assert "ㅎㅎ" in responder.respond("ㅋㅋ")
    assert "다음에" in responder.respond("bye")
